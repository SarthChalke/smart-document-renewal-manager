"""Document renewal routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models import Document, DocumentRenewal
from app.forms import DocumentRenewForm
from app.services.document_service import validate_uploaded_file, save_document_file
from app.services.notification_service import create_renewal_reminder

renewals_bp = Blueprint('renewals', __name__, url_prefix='/renewals')


@renewals_bp.route('/')
@login_required
def renewal_history():
    """Show all renewal history."""
    uid = current_user.id
    today = date.today()

    expiring_and_expired = Document.query.filter(
        Document.user_id == uid,
        Document.expiry_date.isnot(None)
    ).order_by(Document.expiry_date.asc()).all()

    renewal_records = DocumentRenewal.query.filter_by(user_id=uid).order_by(
        DocumentRenewal.created_at.desc()
    ).all()

    return render_template(
        'renewals/index.html',
        documents=expiring_and_expired,
        renewals=renewal_records,
        renewal_statuses=['Not Started', 'Applied', 'In Progress', 'Completed', 'Rejected']
    )


@renewals_bp.route('/<int:document_id>/renew', methods=['GET', 'POST'])
@login_required
def renew_document(document_id):
    """Renew a document."""
    doc = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        app_date_str = request.form.get('application_date', '').strip()
        expected_date_str = request.form.get('expected_completion_date', '').strip()
        actual_date_str = request.form.get('actual_renewal_date', '').strip()
        new_expiry_str = request.form.get('new_expiry_date', '').strip()
        status = request.form.get('status', 'Applied').strip()
        notes = request.form.get('notes', '').strip()

        app_d = datetime.strptime(app_date_str, '%Y-%m-%d').date() if app_date_str else date.today()
        exp_d = datetime.strptime(expected_date_str, '%Y-%m-%d').date() if expected_date_str else None
        act_d = datetime.strptime(actual_date_str, '%Y-%m-%d').date() if actual_date_str else None
        new_exp_d = datetime.strptime(new_expiry_str, '%Y-%m-%d').date() if new_expiry_str else None

        renewed_filename = None
        if 'renewed_file' in request.files and request.files['renewed_file'].filename:
            file = request.files['renewed_file']
            errors = validate_uploaded_file(file)
            if not errors:
                renewed_filename, _, _, _ = save_document_file(file, current_user.id)

        renewal = DocumentRenewal(
            document_id=doc.id,
            user_id=current_user.id,
            application_date=app_d,
            expected_completion_date=exp_d,
            actual_renewal_date=act_d,
            previous_expiry_date=doc.expiry_date,
            new_expiry_date=new_exp_d,
            status=status,
            renewed_document_filename=renewed_filename,
            notes=notes
        )
        db.session.add(renewal)

        # Update document state
        doc.renewal_status = status
        if status == 'Completed' and new_exp_d:
            doc.expiry_date = new_exp_d

        # Create reminder if expected date is set
        if exp_d:
            create_renewal_reminder(renewal)

        db.session.commit()

        flash(f"Renewal record for '{doc.title}' saved.", 'success')
        return redirect(url_for('documents.detail', id=doc.id))

    return render_template('renewals/renew.html', doc=doc)