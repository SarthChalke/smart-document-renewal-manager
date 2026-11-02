"""Government services routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.models import (
    GovernmentApplication, GovernmentCertificateType, GovernmentApplicationDocument,
    GovernmentCertificateRequirement, GovernmentApplicationFee
)
from app.forms import GovernmentApplicationForm, GovernmentApplicationStatusForm
from app.services.document_service import save_document_file, validate_uploaded_file, get_document_path, delete_document_file
from app.services.report_service import generate_government_acknowledgement_pdf
from app.utils.helpers import generate_application_number

import os

government_bp = Blueprint('government', __name__, url_prefix='/government')


@government_bp.route('/')
@login_required
def government_services():
    """Main government services page - certificate catalog with dynamic filtering."""
    # Get filter parameters
    certificate_type = request.args.get('certificate_type', '')
    status = request.args.get('status', '')

    # Base query
    query = GovernmentApplication.query.filter_by(user_id=current_user.id)

    # Apply filters
    if certificate_type:
        query = query.filter_by(service_type=certificate_type)

    if status:
        query = query.filter_by(status=status)

    applications = query.order_by(GovernmentApplication.created_at.desc()).all()

    # Get available certificate types with counts
    certificate_types = GovernmentCertificateType.query.filter_by(is_active=True).all()

    # Get available statuses
    statuses = ['draft', 'submitted_by_user', 'in_progress', 'completed', 'rejected', 'cancelled']

    # Get statistics
    total_applications = len(applications)
    draft_count = sum(1 for app in applications if app.status == 'draft')
    submitted_count = sum(1 for app in applications if app.status == 'submitted_by_user')
    in_progress_count = sum(1 for app in applications if app.status == 'in_progress')
    completed_count = sum(1 for app in applications if app.status == 'completed')

    return render_template(
        'government/services.html',
        applications=applications,
        certificate_types=certificate_types,
        certificate_type=certificate_type,
        statuses=statuses,
        current_status=status,
        total_applications=total_applications,
        draft_count=draft_count,
        submitted_count=submitted_count,
        in_progress_count=in_progress_count,
        completed_count=completed_count
    )


@government_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_for_certificate():
    """Show certificate catalog and handle application creation."""
    # Get all active certificate types with requirements and fees
    certificate_types = GovernmentCertificateType.query.filter_by(is_active=True).order_by('name').all()

    if request.method == 'POST':
        selected_type_id = request.form.get('certificate_type_id')
        if not selected_type_id:
            flash('Please select a certificate type.', 'danger')
            return render_template('government/apply.html', certificate_types=certificate_types)

        certificate_type = GovernmentCertificateType.query.get_or_404(selected_type_id)

        # Create application
        application = GovernmentApplication(
            user_id=current_user.id,
            service_type=certificate_type.name,
            applicant_name=request.form.get('applicant_name', '').strip(),
            district=request.form.get('district', '').strip(),
            status='draft'
        )

        # Parse dates
        if request.form.get('application_date'):
            application.application_date = datetime.strptime(
                request.form.get('application_date'), '%Y-%m-%d'
            ).date()

        if request.form.get('expected_completion_date'):
            application.expected_completion_date = datetime.strptime(
                request.form.get('expected_completion_date'), '%Y-%m-%d'
            ).date()

        # Add notes
        application.notes = request.form.get('notes', '').strip()

        # Generate application number
        application.application_number = generate_application_number('GOV')

        db.session.add(application)
        db.session.flush()

        # Create application document records for required documents
        for requirement in certificate_type.requirements:
            app_doc = GovernmentApplicationDocument(
                application_id=application.id,
                requirement_id=requirement.id,
                status='pending'
            )
            db.session.add(app_doc)

        # Create application fee record
        total_fee = sum(req.fee_amount for req in certificate_type.requirements)
        if total_fee > 0:
            app_fee = GovernmentApplicationFee(
                application_id=application.id,
                fee_amount=total_fee,
                payment_status='pending'
            )
            db.session.add(app_fee)

        db.session.commit()

        flash(f'Application for {certificate_type.name} created successfully. Application # {application.application_number}', 'success')
        return redirect(url_for('government.view_application', application_id=application.id))

    return render_template('government/apply.html', certificate_types=certificate_types)


@government_bp.route('/<int:application_id>')
@login_required
def view_application(application_id):
    """View application details and status."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Get related data
    documents = GovernmentApplicationDocument.query.filter_by(
        application_id=application_id
    ).all()

    fee = GovernmentApplicationFee.query.filter_by(
        application_id=application_id
    ).first()

    return render_template(
        'government/view_application.html',
        application=application,
        documents=documents,
        fee=fee
    )


@government_bp.route('/<int:application_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(application_id):
    """Edit application details."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Only allow editing if still in draft status
    if application.status != 'draft':
        flash('Cannot edit application once submitted.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    if request.method == 'POST':
        application.applicant_name = request.form.get('applicant_name', '').strip()
        application.district = request.form.get('district', '').strip()

        if request.form.get('application_date'):
            application.application_date = datetime.strptime(
                request.form.get('application_date'), '%Y-%m-%d'
            ).date()

        if request.form.get('expected_completion_date'):
            application.expected_completion_date = datetime.strptime(
                request.form.get('expected_completion_date'), '%Y-%m-%d'
            ).date()

        application.notes = request.form.get('notes', '').strip()

        db.session.commit()

        flash('Application updated successfully.', 'success')
        return redirect(url_for('government.view_application', application_id=application_id))

    return render_template(
        'government/edit_application.html',
        application=application
    )


@government_bp.route('/<int:application_id>/submit')
@login_required
def submit_application(application_id):
    """Submit application through official portal (local tracking only)."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Update status
    application.status = 'submitted_by_user'
    application.submitted_date = date.today()

    db.session.commit()

    flash('Application submitted through official portal. Status updated locally.', 'success')
    return redirect(url_for('government.view_application', application_id=application_id))


@government_bp.route('/<int:application_id>/cancel')
@login_required
def cancel_application(application_id):
    """Cancel application."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Update status
    application.status = 'cancelled'

    db.session.commit()

    flash('Application cancelled.', 'info')
    return redirect(url_for('government.government_services'))


@government_bp.route('/<int:application_id>/documents', methods=['POST'])
@login_required
def upload_application_document(application_id):
    """Upload a document for a government application."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Only allow upload for applications in draft or submitted status
    if application.status not in ['draft', 'submitted_by_user']:
        flash('Cannot upload documents for applications in this status.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    if 'document_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    file = request.files['document_file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    # Find which requirement this file corresponds to
    requirement_id = request.form.get('requirement_id')
    if not requirement_id:
        flash('Requirement not specified.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    requirement = GovernmentCertificateRequirement.query.get_or_404(requirement_id)

    # Check if file already uploaded for this requirement
    existing_doc = GovernmentApplicationDocument.query.filter_by(
        application_id=application_id,
        requirement_id=requirement_id
    ).first()

    if existing_doc and existing_doc.file_path:
        # Delete old file
        if existing_doc.file_path:
            delete_document_file(existing_doc.file_path)
        existing_doc.file_path = None
        existing_doc.file_name = None
        existing_doc.file_size = None

    # Validate and save file
    errors = validate_uploaded_file(file)
    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    saved_name, orig_name, size, mime = save_document_file(file, current_user.id)

    # Update document record
    if existing_doc:
        existing_doc.file_path = saved_name
        existing_doc.file_name = orig_name
        existing_doc.file_size = size
        existing_doc.mime_type = mime
        existing_doc.uploaded_at = datetime.utcnow()
        document = existing_doc
    else:
        document = GovernmentApplicationDocument(
            application_id=application_id,
            requirement_id=requirement_id,
            file_path=saved_name,
            file_name=orig_name,
            file_size=size,
            mime_type=mime,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(document)

    # Update requirement status
    requirement.status = 'uploaded'

    db.session.commit()

    flash(f'Document {orig_name} uploaded successfully.', 'success')
    return redirect(url_for('government.view_application', application_id=application_id))


@government_bp.route('/<int:application_id>/documents/<int:document_id>/delete')
@login_required
def delete_application_document(application_id, document_id):
    """Delete a document for a government application."""
    document = GovernmentApplicationDocument.query.filter_by(
        id=document_id, application_id=application_id
    ).first_or_404()

    # Check ownership
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Delete file from disk
    if document.file_path:
        delete_document_file(document.file_path)

    db.session.delete(document)
    db.session.commit()

    flash('Document deleted successfully.', 'info')
    return redirect(url_for('government.view_application', application_id=application_id))


@government_bp.route('/<int:application_id>/download-acknowledgement')
@login_required
def download_acknowledgement(application_id):
    """Download acknowledgement PDF for a government application."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    # Generate PDF
    pdf_path = generate_government_acknowledgement_pdf(application_id)

    if not pdf_path or not os.path.exists(pdf_path):
        flash('Acknowledgement PDF could not be generated.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f'acknowledgement_{application.application_number}.pdf'
    )


@government_bp.route('/<int:application_id>/status', methods=['POST'])
@login_required
def update_application_status(application_id):
    """Update application status."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    new_status = request.form.get('status', '').strip()
    valid_statuses = ['draft', 'submitted_by_user', 'in_progress', 'completed', 'rejected', 'cancelled']

    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('government.view_application', application_id=application_id))

    application.status = new_status

    db.session.commit()

    flash('Application status updated.', 'success')
    return redirect(url_for('government.view_application', application_id=application_id))