"""Document renewal routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Document, DocumentRenewalHistory
from app.forms import DocumentRenewForm
from app.services.document_service import validate_file, save_uploaded_file

renewals_bp = Blueprint('renewals', __name__, url_prefix='/renewals')


@renewals_bp.route('/')
@login_required
def renewal_history():
    """Show all renewal history."""
    page = request.args.get('page', 1, type=int)

    renewals = db.session.query(DocumentRenewalHistory, Document).join(
        Document, DocumentRenewalHistory.document_id == Document.id
    ).filter(
        Document.user_id == current_user.id
    ).order_by(DocumentRenewalHistory.renewed_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('renewals/history.html', renewals=renewals)


@renewals_bp.route('/document/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def renew_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)

    form = DocumentRenewForm()
    if form.validate_on_submit():
        # Save renewal history
        renewal = DocumentRenewalHistory(
            document_id=doc.id,
            previous_expiry_date=doc.expiry_date,
            previous_issue_date=doc.issue_date,
            new_expiry_date=form.new_expiry_date.data,
            new_issue_date=form.new_issue_date.data,
            notes=form.notes.data,
        )

        # Handle new document file
        if form.file.data:
            file = form.file.data
            errors = validate_file(file)
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('renewals/renew.html', form=form, doc=doc)

            filename, original_filename, file_size, mime_type = save_uploaded_file(file, current_user.id)
            renewal.renewal_document_filename = filename
            doc.filename = filename
            doc.original_filename = original_filename
            doc.file_size = file_size
            doc.mime_type = mime_type

        # Update document dates
        if form.new_issue_date.data:
            doc.issue_date = form.new_issue_date.data
        if form.new_expiry_date.data:
            doc.expiry_date = form.new_expiry_date.data

        db.session.add(renewal)
        db.session.commit()

        flash('Document renewed successfully!', 'success')
        return redirect(url_for('documents.view_document', doc_id=doc.id))

    return render_template('renewals/renew.html', form=form, doc=doc)


@renewals_bp.route('/document/<int:doc_id>/history')
@login_required
def document_renewal_history(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)

    renewals = DocumentRenewalHistory.query.filter_by(document_id=doc.id) \
        .order_by(DocumentRenewalHistory.renewed_at.desc()).all()

    return render_template('renewals/document_history.html', doc=doc, renewals=renewals)
