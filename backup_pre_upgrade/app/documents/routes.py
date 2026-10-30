"""Document management routes."""
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Document, DOCUMENT_CATEGORIES, DOCUMENT_CATEGORY_DICT
from app.forms import DocumentUploadForm, DocumentEditForm, DocumentOCRForm
from app.services.document_service import validate_file, save_uploaded_file, get_file_path, delete_uploaded_file
from app.services.ocr_service import extract_text_from_file, extract_document_info
from datetime import datetime

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


@documents_bp.route('/')
@login_required
def list_documents():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    sort = request.args.get('sort', 'uploaded_desc').strip()

    query = Document.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            (Document.title.ilike(f'%{search}%')) |
            (Document.document_number.ilike(f'%{search}%'))
        )

    if category:
        query = query.filter_by(category=category)

    # Sort
    if sort == 'expiry_asc':
        query = query.order_by(Document.expiry_date.asc().nullslast())
    elif sort == 'expiry_desc':
        query = query.order_by(Document.expiry_date.desc().nullslast())
    elif sort == 'uploaded_asc':
        query = query.order_by(Document.uploaded_at.asc())
    else:
        query = query.order_by(Document.uploaded_at.desc())

    documents = query.paginate(page=page, per_page=12, error_out=False)

    # Filter by status after query (computed property)
    if status:
        filtered_items = [d for d in documents.items if d.expiry_status == status]
    else:
        filtered_items = documents.items

    return render_template('documents/list.html',
                           documents=documents,
                           filtered_items=filtered_items,
                           categories=DOCUMENT_CATEGORIES,
                           search=search,
                           current_category=category,
                           current_status=status,
                           current_sort=sort)


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = DocumentUploadForm()
    if form.validate_on_submit():
        file = form.file.data

        # Validate file
        errors = validate_file(file)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('documents/upload.html', form=form)

        # Save file
        filename, original_filename, file_size, mime_type = save_uploaded_file(file, current_user.id)

        doc = Document(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            document_number=form.document_number.data,
            issue_date=form.issue_date.data,
            expiry_date=form.expiry_date.data,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
        )
        db.session.add(doc)
        db.session.commit()

        flash('Document uploaded successfully!', 'success')
        return redirect(url_for('documents.view_document', doc_id=doc.id))

    return render_template('documents/upload.html', form=form)


@documents_bp.route('/upload-ocr', methods=['GET', 'POST'])
@login_required
def upload_with_ocr():
    """Upload with OCR extraction - two-step process."""
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']

        errors = validate_file(file)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('documents/upload_ocr.html', step='upload')

        # Save file temporarily
        filename, original_filename, file_size, mime_type = save_uploaded_file(file, current_user.id)
        filepath = get_file_path(filename, current_user.id)

        # Extract text
        extracted_text = ''
        extracted_info = {'document_numbers': [], 'issue_dates': [], 'expiry_dates': []}

        if filepath:
            extracted_text = extract_text_from_file(filepath)
            if extracted_text:
                extracted_info = extract_document_info(extracted_text)

        # Show editable form with extracted data
        form = DocumentOCRForm()
        form.document_number.data = extracted_info['document_numbers'][0] if extracted_info['document_numbers'] else ''

        if extracted_info['issue_dates']:
            try:
                form.issue_date.data = datetime.strptime(extracted_info['issue_dates'][0], '%Y-%m-%d').date()
            except (ValueError, IndexError):
                pass

        if extracted_info['expiry_dates']:
            try:
                form.expiry_date.data = datetime.strptime(extracted_info['expiry_dates'][0], '%Y-%m-%d').date()
            except (ValueError, IndexError):
                pass

        return render_template('documents/upload_ocr.html',
                               step='confirm',
                               form=form,
                               filename=filename,
                               original_filename=original_filename,
                               file_size=file_size,
                               mime_type=mime_type,
                               extracted_text=extracted_text[:2000] if extracted_text else '',
                               extracted_info=extracted_info)

    # Handle confirmation step
    if request.method == 'POST' and 'confirm' in request.form:
        form = DocumentOCRForm()
        if form.validate_on_submit():
            doc = Document(
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                category=form.category.data,
                document_number=form.document_number.data,
                issue_date=form.issue_date.data,
                expiry_date=form.expiry_date.data,
                filename=request.form.get('filename'),
                original_filename=request.form.get('original_filename'),
                file_size=int(request.form.get('file_size', 0)),
                mime_type=request.form.get('mime_type', 'application/octet-stream'),
            )
            db.session.add(doc)
            db.session.commit()

            flash('Document saved with extracted data!', 'success')
            return redirect(url_for('documents.view_document', doc_id=doc.id))

        return render_template('documents/upload_ocr.html', step='confirm', form=form)

    return render_template('documents/upload_ocr.html', step='upload')


@documents_bp.route('/<int:doc_id>')
@login_required
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)
    return render_template('documents/view.html', doc=doc)


@documents_bp.route('/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)

    form = DocumentEditForm(obj=doc)
    if form.validate_on_submit():
        doc.title = form.title.data
        doc.description = form.description.data
        doc.category = form.category.data
        doc.document_number = form.document_number.data
        doc.issue_date = form.issue_date.data
        doc.expiry_date = form.expiry_date.data
        db.session.commit()
        flash('Document updated.', 'success')
        return redirect(url_for('documents.view_document', doc_id=doc.id))

    return render_template('documents/edit.html', form=form, doc=doc)


@documents_bp.route('/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)

    delete_uploaded_file(doc.filename, current_user.id)
    db.session.delete(doc)
    db.session.commit()
    flash('Document deleted.', 'success')
    return redirect(url_for('documents.list_documents'))


@documents_bp.route('/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        abort(403)

    filepath = get_file_path(doc.filename, current_user.id)
    if not filepath:
        abort(404)

    return send_file(filepath, as_attachment=True,
                     download_name=doc.original_filename or doc.filename)


@documents_bp.route('/expiry-reminders')
@login_required
def expiry_reminders():
    """Show documents grouped by expiry status."""
    docs = Document.query.filter(
        Document.user_id == current_user.id,
        Document.expiry_date.isnot(None)
    ).order_by(Document.expiry_date.asc()).all()

    expired = [d for d in docs if d.expiry_status == 'expired']
    expiring = [d for d in docs if d.expiry_status == 'expiring_soon']
    valid = [d for d in docs if d.expiry_status == 'valid']

    return render_template('documents/expiry_reminders.html',
                           expired=expired,
                           expiring=expiring,
                           valid=valid)
