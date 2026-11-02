"""Document management routes."""
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Document, DOCUMENT_CATEGORIES, DOCUMENT_CATEGORY_DICT
from app.forms import DocumentUploadForm, DocumentEditForm, DocumentOCRForm
from app.services.document_service import validate_uploaded_file, save_document_file, get_document_path, delete_document_file
from app.services.ocr_service import extract_text_from_file
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


@documents_bp.route('/')
@login_required
def list_documents():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip()
    sort = request.args.get('sort', 'newest').strip()

    query = Document.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            (Document.title.ilike(f'%{search}%')) |
            (Document.document_number.ilike(f'%{search}%')) |
            (Document.holder_name.ilike(f'%{search}%')) |
            (Document.issuing_authority.ilike(f'%{search}%'))
        )

    if category:
        query = query.filter_by(category=category)

    if sort == 'expiry_asc':
        query = query.order_by(Document.expiry_date.asc().nullslast())
    elif sort == 'expiry_desc':
        query = query.order_by(Document.expiry_date.desc().nullslast())
    elif sort == 'oldest':
        query = query.order_by(Document.created_at.asc())
    else:
        query = query.order_by(Document.created_at.desc())

    all_matching = query.all()

    # Filter status dynamically
    if status_filter:
        filtered_items = [d for d in all_matching if d.expiry_status == status_filter]
    else:
        filtered_items = all_matching

    # Simple pagination
    per_page = 12
    total_items = len(filtered_items)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    paged_items = filtered_items[start_idx:start_idx + per_page]

    return render_template(
        'documents.html',
        documents=paged_items,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        search=search,
        current_category=category,
        current_status=status_filter,
        current_sort=sort,
        categories=DOCUMENT_CATEGORIES
    )


@documents_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_document():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        document_number = request.form.get('document_number', '').strip()
        issuing_authority = request.form.get('issuing_authority', '').strip()
        holder_name = request.form.get('holder_name', '').strip()
        issue_date_str = request.form.get('issue_date', '').strip()
        expiry_date_str = request.form.get('expiry_date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not title or not category:
            flash('Document title and category are required.', 'danger')
            return render_template('documents/add_document.html', categories=DOCUMENT_CATEGORIES)

        file = request.files.get('document_file')
        errors = validate_uploaded_file(file)
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('documents/add_document.html', categories=DOCUMENT_CATEGORIES)

        saved_name, orig_name, size, mime = save_document_file(file, current_user.id)

        issue_d = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
        expiry_d = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

        doc = Document(
            user_id=current_user.id,
            title=title,
            category=category,
            document_number=document_number,
            issuing_authority=issuing_authority,
            holder_name=holder_name,
            issue_date=issue_d,
            expiry_date=expiry_d,
            notes=notes,
            filename=saved_name,
            original_filename=orig_name,
            file_size=size,
            mime_type=mime,
            expiry_status=calculate_expiry_status(expiry_d)
        )
        db.session.add(doc)
        db.session.commit()

        flash(f"Document '{doc.title}' added successfully!", 'success')
        return redirect(url_for('documents.detail', id=doc.id))

    return render_template('documents/add_document.html', categories=DOCUMENT_CATEGORIES)


@documents_bp.route('/<int:id>')
@login_required
def detail(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    renewals = doc.renewals.all()
    return render_template('documents/detail.html', doc=doc, renewals=renewals)


@documents_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        doc.title = request.form.get('title', '').strip()
        doc.category = request.form.get('category', '').strip()
        doc.document_number = request.form.get('document_number', '').strip()
        doc.issuing_authority = request.form.get('issuing_authority', '').strip()
        doc.holder_name = request.form.get('holder_name', '').strip()
        doc.notes = request.form.get('notes', '').strip()

        issue_str = request.form.get('issue_date', '').strip()
        expiry_str = request.form.get('expiry_date', '').strip()

        doc.issue_date = datetime.strptime(issue_str, '%Y-%m-%d').date() if issue_str else None
        doc.expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None
        doc.expiry_status = calculate_expiry_status(doc.expiry_date)

        # Optional replacement file
        if 'document_file' in request.files and request.files['document_file'].filename:
            file = request.files['document_file']
            errors = validate_uploaded_file(file)
            if not errors:
                delete_document_file(doc.filename)
                saved_name, orig_name, size, mime = save_document_file(file, current_user.id)
                doc.filename = saved_name
                doc.original_filename = orig_name
                doc.file_size = size
                doc.mime_type = mime

        db.session.commit()
        flash('Document details updated successfully.', 'success')
        return redirect(url_for('documents.detail', id=doc.id))

    return render_template('documents/edit_document.html', doc=doc, categories=DOCUMENT_CATEGORIES)


@documents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    title = doc.title
    file_path = get_document_path(doc.filename)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(doc)
    db.session.commit()
    flash(f"Document '{title}' deleted.", 'info')
    return redirect(url_for('documents.list_documents'))


@documents_bp.route('/<int:id>/download')
@login_required
def download_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    path = get_document_path(doc.filename)
    if not path:
        abort(404, description="Document file not found on disk.")
    return send_file(path, as_attachment=True, download_name=doc.original_filename or doc.filename)


@documents_bp.route('/<int:id>/preview')
@login_required
def preview_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    path = get_document_path(doc.filename)
    if not path:
        abort(404)
    return send_file(path, mimetype=doc.mime_type or 'application/octet-stream')


def calculate_expiry_status(expiry_date):
    """Calculate document expiry status based on expiry date."""
    if not expiry_date:
        return 'no_expiry'

    today = date.today()
    diff = (expiry_date - today).days

    if diff < 0:
        return 'expired'
    elif diff == 0:
        return 'expiring_today'
    elif diff <= 7:
        return 'expiring_soon'
    elif diff <= 30:
        return 'expiring_soon'
    else:
        return 'valid'