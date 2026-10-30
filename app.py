import os
import io
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, send_file, Response, abort)
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import (db, User, Document, DocumentRenewal, Loan, EMISchedule,
                    LoanPayment, PaymentReceipt, Notification, AuditLog,
                    UserReminderPreference, GovernmentApplication,
                    DOCUMENT_CATEGORIES, DOCUMENT_CATEGORY_DICT,
                    LOAN_TYPES, LOAN_TYPE_DICT, LOAN_STATUSES, PAYMENT_METHODS,
                    PAYMENT_STATUSES, RENEWAL_STATUSES)
from services.ocr_service import (extract_text_from_file, parse_document_text,
                                  is_tesseract_available)
from services.document_service import (validate_uploaded_file, save_document_file,
                                       save_receipt_file, get_document_path,
                                       delete_document_file)
from services.emi_service import (calculate_emi, generate_loan_emi_schedule,
                                  update_all_emi_statuses, record_emi_payment,
                                  record_general_loan_payment, cancel_payment_record,
                                  round_curr)
from services.notification_service import (trigger_all_reminders_for_user)
from services.report_service import (generate_payment_receipt_pdf,
                                     generate_loans_summary_pdf,
                                     generate_emi_schedule_pdf,
                                     export_documents_csv, export_loans_csv,
                                     export_payments_csv)

# Initialize App
app = Flask(__name__)
app.config.from_object(Config)

# Ensure instance and upload directories exist
os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
os.makedirs(Config.DOCUMENTS_FOLDER, exist_ok=True)
os.makedirs(Config.RECEIPTS_FOLDER, exist_ok=True)

# Initialize Extensions
db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Helper for client IP
def get_client_ip():
    if request:
        return request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
    return '127.0.0.1'


# Context Processor to inject notification counts and utility data into all templates
@app.context_processor
def inject_globals():
    unread_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            user_id=current_user.id, is_read=False
        ).count()
    return {
        'unread_notification_count': unread_count,
        'now': datetime.utcnow(),
        'today': date.today(),
        'csrf_token': generate_csrf,
        'doc_categories': DOCUMENT_CATEGORIES,
        'loan_types': LOAN_TYPES,
        'tesseract_installed': is_tesseract_available()
    }


# Auto-create tables on startup
with app.app_context():
    db.create_all()


# ─── AUTHENTICATION ROUTES ───────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not full_name or not username or not email or not password:
            flash('All required fields must be filled.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please login.', 'danger')
            return render_template('register.html')

        # Create user
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Create default reminder preferences
        pref = UserReminderPreference(
            user_id=user.id,
            doc_days_before='30,14,7,1',
            emi_days_before='7,3,1,0',
            in_app_enabled=True,
            email_enabled=False
        )
        db.session.add(pref)

        # Audit log
        audit = AuditLog(
            user_id=user.id,
            action='USER_REGISTERED',
            entity_type='User',
            entity_id=user.id,
            details=f"User {username} registered successfully.",
            ip_address=get_client_ip()
        )
        db.session.add(audit)
        db.session.commit()

        flash('Registration successful! Please login with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            # Trigger reminder check on login
            trigger_all_reminders_for_user(user.id)
            update_all_emi_statuses(user.id)

            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next', '')
            # Only allow local relative paths for post-login redirects.
            if next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('login'))


# ─── DASHBOARD ROUTE ─────────────────────────────────────────

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    uid = current_user.id
    today = date.today()
    thirty_days = today + timedelta(days=30)

    # Automatically check reminders & EMI statuses
    update_all_emi_statuses(uid)
    trigger_all_reminders_for_user(uid)

    # 1. Document Statistics
    user_docs = Document.query.filter_by(user_id=uid).all()
    total_docs = len(user_docs)
    valid_docs = sum(1 for d in user_docs if d.expiry_status == 'valid')
    expiring_soon_docs = sum(1 for d in user_docs if d.expiry_status in ('expiring_soon', 'expiring_today'))
    expired_docs = sum(1 for d in user_docs if d.expiry_status == 'expired')
    pending_renewals = DocumentRenewal.query.filter(
        DocumentRenewal.user_id == uid,
        DocumentRenewal.status.in_(['Applied', 'In Progress'])
    ).count()

    # 2. Financial Statistics
    user_loans = Loan.query.filter_by(user_id=uid).all()
    total_active_loans = sum(1 for l in user_loans if l.status == 'active')
    total_loan_amount = sum(Decimal(str(l.principal_amount)) for l in user_loans)
    total_eligible_paid = sum(l.total_eligible_paid for l in user_loans)
    total_outstanding_principal = sum(l.estimated_outstanding_principal for l in user_loans if l.status == 'active')
    total_monthly_emi = sum(Decimal(str(l.monthly_emi)) for l in user_loans if l.status == 'active')

    # 3. EMI Statistics
    all_emis = EMISchedule.query.filter_by(user_id=uid).all()
    emis_due_today = sum(1 for e in all_emis if e.due_date == today and e.status != 'paid')
    upcoming_emis = sum(1 for e in all_emis if e.due_date > today and e.due_date <= thirty_days and e.status != 'paid')
    overdue_emis = sum(1 for e in all_emis if e.status == 'overdue')

    # 4. Dashboard Lists
    upcoming_doc_expiries = [d for d in user_docs if d.expiry_date and today <= d.expiry_date <= thirty_days]
    upcoming_doc_expiries.sort(key=lambda x: x.expiry_date)
    upcoming_doc_expiries = upcoming_doc_expiries[:5]

    recent_renewals = DocumentRenewal.query.filter_by(user_id=uid).order_by(
        DocumentRenewal.created_at.desc()
    ).limit(5).all()

    upcoming_schedule = EMISchedule.query.filter(
        EMISchedule.user_id == uid,
        EMISchedule.status.in_(['upcoming', 'due_today']),
        EMISchedule.due_date >= today
    ).order_by(EMISchedule.due_date.asc()).limit(5).all()

    overdue_alerts = EMISchedule.query.filter(
        EMISchedule.user_id == uid,
        EMISchedule.status == 'overdue'
    ).order_by(EMISchedule.due_date.asc()).limit(5).all()

    recent_payments = LoanPayment.query.filter_by(user_id=uid).order_by(
        LoanPayment.payment_date.desc(), LoanPayment.created_at.desc()
    ).limit(5).all()

    return render_template(
        'dashboard.html',
        total_docs=total_docs,
        valid_docs=valid_docs,
        expiring_soon_docs=expiring_soon_docs,
        expired_docs=expired_docs,
        pending_renewals=pending_renewals,
        total_active_loans=total_active_loans,
        total_loan_amount=total_loan_amount,
        total_eligible_paid=total_eligible_paid,
        total_outstanding_principal=total_outstanding_principal,
        total_monthly_emi=total_monthly_emi,
        emis_due_today=emis_due_today,
        upcoming_emis=upcoming_emis,
        overdue_emis=overdue_emis,
        upcoming_doc_expiries=upcoming_doc_expiries,
        recent_renewals=recent_renewals,
        upcoming_schedule=upcoming_schedule,
        overdue_alerts=overdue_alerts,
        recent_payments=recent_payments,
        user_loans=user_loans
    )


@app.route('/api/dashboard-charts')
@login_required
def api_dashboard_charts():
    uid = current_user.id
    docs = Document.query.filter_by(user_id=uid).all()

    # Document Status Breakdown
    doc_status = {
        'Valid': sum(1 for d in docs if d.expiry_status == 'valid'),
        'Expiring Soon': sum(1 for d in docs if d.expiry_status in ('expiring_soon', 'expiring_today')),
        'Expired': sum(1 for d in docs if d.expiry_status == 'expired'),
        'Renewed': sum(1 for d in docs if d.expiry_status == 'renewed'),
        'No Expiry': sum(1 for d in docs if d.expiry_status == 'no_expiry')
    }

    # Loan Status Distribution
    loans = Loan.query.filter_by(user_id=uid).all()
    loan_status = {}
    for l in loans:
        s = l.status.title()
        loan_status[s] = loan_status.get(s, 0) + 1

    # Principal vs Interest across all user loans
    tot_principal = sum(float(l.principal_amount) for l in loans)
    tot_payable = sum(float(l.total_amount_payable) for l in loans)
    tot_interest = max(0.0, tot_payable - tot_principal)

    # Monthly Payments (past 6 months)
    today = date.today()
    monthly_payments = {}
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 30)
        label = m_date.strftime('%b %Y')
        m_start = m_date.replace(day=1)
        if m_date.month == 12:
            m_end = m_date.replace(year=m_date.year + 1, month=1, day=1)
        else:
            m_end = m_date.replace(month=m_date.month + 1, day=1)

        total_paid_in_month = db.session.query(db.func.sum(LoanPayment.amount)).filter(
            LoanPayment.user_id == uid,
            LoanPayment.payment_status == 'completed',
            LoanPayment.payment_date >= m_start,
            LoanPayment.payment_date < m_end
        ).scalar() or 0
        monthly_payments[label] = float(total_paid_in_month)

    return jsonify({
        'doc_status': doc_status,
        'loan_status': loan_status,
        'principal_vs_interest': {
            'Principal': tot_principal,
            'Total Interest': tot_interest
        },
        'monthly_payments': monthly_payments
    })


# ─── DOCUMENT MANAGEMENT ROUTES ──────────────────────────────

@app.route('/documents')
@login_required
def documents_list():
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


@app.route('/documents/add', methods=['GET', 'POST'])
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
            return render_template('add_document.html', categories=DOCUMENT_CATEGORIES)

        file = request.files.get('document_file')
        errors = validate_uploaded_file(file)
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('add_document.html', categories=DOCUMENT_CATEGORIES)

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
            mime_type=mime
        )
        db.session.add(doc)
        db.session.commit()

        # Audit
        audit = AuditLog(
            user_id=current_user.id,
            action='DOCUMENT_UPLOADED',
            entity_type='Document',
            entity_id=doc.id,
            details=f"Uploaded document '{doc.title}' ({doc.category_display}).",
            ip_address=get_client_ip()
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Document '{doc.title}' added successfully!", 'success')
        return redirect(url_for('document_details', id=doc.id))

    return render_template('add_document.html', categories=DOCUMENT_CATEGORIES)


@app.route('/documents/<int:id>')
@login_required
def document_details(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    renewals = doc.renewals.all()
    return render_template('document_details.html', doc=doc, renewals=renewals)


@app.route('/documents/<int:id>/edit', methods=['GET', 'POST'])
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

        # Optional replacement file
        if 'document_file' in request.files and request.files['document_file'].filename:
            file = request.files['document_file']
            errors = validate_uploaded_file(file)
            if errors:
                for err in errors:
                    flash(err, 'danger')
                return render_template('document_details.html', doc=doc, edit_mode=True, categories=DOCUMENT_CATEGORIES)
            
            # Delete old file
            delete_document_file(doc.filename)
            saved_name, orig_name, size, mime = save_document_file(file, current_user.id)
            doc.filename = saved_name
            doc.original_filename = orig_name
            doc.file_size = size
            doc.mime_type = mime

        db.session.commit()
        flash('Document details updated successfully.', 'success')
        return redirect(url_for('document_details', id=doc.id))

    return render_template('document_details.html', doc=doc, edit_mode=True, categories=DOCUMENT_CATEGORIES)


@app.route('/documents/<int:id>/delete', methods=['POST'])
@login_required
def delete_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    title = doc.title
    delete_document_file(doc.filename)
    db.session.delete(doc)
    db.session.commit()
    flash(f"Document '{title}' deleted.", 'info')
    return redirect(url_for('documents_list'))


@app.route('/documents/<int:id>/download')
@login_required
def download_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    path = get_document_path(doc.filename)
    if not path:
        abort(404, description="Document file not found on disk.")
    return send_file(path, as_attachment=True, download_name=doc.original_filename or doc.filename)


@app.route('/documents/<int:id>/preview')
@login_required
def preview_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    path = get_document_path(doc.filename)
    if not path:
        abort(404)
    return send_file(path, mimetype=doc.mime_type or 'application/octet-stream')


# ─── SCAN DOCUMENT & OCR ROUTES ──────────────────────────────

@app.route('/scan-document')
@login_required
def scan_document():
    return render_template('scan_document.html', categories=DOCUMENT_CATEGORIES)


@app.route('/api/ocr-process', methods=['POST'])
@login_required
def api_ocr_process():
    """Receives captured camera photo or uploaded image file and returns OCR results."""
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No image data received.'}), 400

    errors = validate_uploaded_file(file)
    if errors:
        return jsonify({'success': False, 'message': errors[0]}), 400

    # Save to temp location for OCR
    saved_name, orig_name, size, mime = save_document_file(file, current_user.id)
    full_path = get_document_path(saved_name)

    ocr_result = extract_text_from_file(full_path)
    raw_text = ocr_result.get('text', '')
    parsed_info = parse_document_text(raw_text)

    return jsonify({
        'success': True,
        'tesseract_available': ocr_result.get('tesseract_available', False),
        'message': ocr_result.get('message', ''),
        'raw_text': raw_text,
        'extracted': parsed_info,
        'temp_filename': saved_name,
        'original_filename': orig_name,
        'file_size': size,
        'mime_type': mime
    })


@app.route('/documents/save-scanned', methods=['POST'])
@login_required
def save_scanned_document():
    temp_filename = request.form.get('temp_filename', '').strip()
    title = request.form.get('title', '').strip()
    category = request.form.get('category', '').strip()
    document_number = request.form.get('document_number', '').strip()
    issuing_authority = request.form.get('issuing_authority', '').strip()
    holder_name = request.form.get('holder_name', '').strip()
    issue_date_str = request.form.get('issue_date', '').strip()
    expiry_date_str = request.form.get('expiry_date', '').strip()
    notes = request.form.get('notes', '').strip()
    orig_name = request.form.get('original_filename', 'scanned_doc.png')
    size = int(request.form.get('file_size', 0))
    mime = request.form.get('mime_type', 'image/png')

    if not temp_filename or not get_document_path(temp_filename):
        flash('Scanned file missing. Please scan or upload again.', 'danger')
        return redirect(url_for('scan_document'))

    if not title or not category:
        flash('Title and Category are required.', 'danger')
        return redirect(url_for('scan_document'))

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
        filename=temp_filename,
        original_filename=orig_name,
        file_size=size,
        mime_type=mime
    )
    db.session.add(doc)
    db.session.commit()

    flash(f"Scanned document '{doc.title}' saved successfully!", 'success')
    return redirect(url_for('document_details', id=doc.id))


# ─── DOCUMENT RENEWALS ROUTES ────────────────────────────────

@app.route('/renewals')
@login_required
def renewals_list():
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
        'renewals.html',
        documents=expiring_and_expired,
        renewals=renewal_records,
        renewal_statuses=RENEWAL_STATUSES
    )


@app.route('/documents/<int:id>/renew', methods=['GET', 'POST'])
@login_required
def renew_document(id):
    doc = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()

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
                # Update main document file if completed
                if status == 'Completed':
                    delete_document_file(doc.filename)
                    doc.filename = renewed_filename

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

        # Audit
        audit = AuditLog(
            user_id=current_user.id,
            action='DOCUMENT_RENEWAL_LOGGED',
            entity_type='DocumentRenewal',
            entity_id=doc.id,
            details=f"Renewal for document '{doc.title}' updated to status: {status}.",
            ip_address=get_client_ip()
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Renewal record for '{doc.title}' saved.", 'success')
        return redirect(url_for('document_details', id=doc.id))

    return render_template('renewals.html', doc=doc, start_renewal=True, renewal_statuses=RENEWAL_STATUSES)


# ─── LOAN MANAGEMENT ROUTES ──────────────────────────────────

@app.route('/loans')
@login_required
def loans_list():
    uid = current_user.id
    search = request.args.get('search', '').strip()
    loan_type = request.args.get('loan_type', '').strip()
    status = request.args.get('status', '').strip()

    query = Loan.query.filter_by(user_id=uid)

    if search:
        query = query.filter(
            (Loan.loan_name.ilike(f'%{search}%')) |
            (Loan.lender_name.ilike(f'%{search}%')) |
            (Loan.loan_id_code.ilike(f'%{search}%')) |
            (Loan.loan_reference_number.ilike(f'%{search}%'))
        )
    if loan_type:
        query = query.filter_by(loan_type=loan_type)
    if status:
        query = query.filter_by(status=status)

    loans = query.order_by(Loan.created_at.desc()).all()

    # Summary cards calculation
    all_loans = Loan.query.filter_by(user_id=uid).all()
    active_loans_count = sum(1 for l in all_loans if l.status == 'active')
    total_borrowed = sum(Decimal(str(l.principal_amount)) for l in all_loans)
    total_paid = sum(l.total_eligible_paid for l in all_loans)
    total_outstanding = sum(l.estimated_outstanding_principal for l in all_loans if l.status == 'active')

    return render_template(
        'loans.html',
        loans=loans,
        active_loans_count=active_loans_count,
        total_borrowed=total_borrowed,
        total_paid=total_paid,
        total_outstanding=total_outstanding,
        loan_types=LOAN_TYPES,
        loan_statuses=LOAN_STATUSES,
        search=search,
        current_type=loan_type,
        current_status=status
    )


@app.route('/loans/add', methods=['GET', 'POST'])
@login_required
def add_loan():
    if request.method == 'POST':
        loan_name = request.form.get('loan_name', '').strip()
        loan_type = request.form.get('loan_type', '').strip()
        lender_name = request.form.get('lender_name', '').strip()
        reference_no = request.form.get('loan_reference_number', '').strip()
        principal_str = request.form.get('principal_amount', '0').strip()
        rate_str = request.form.get('annual_interest_rate', '0').strip()
        tenure_str = request.form.get('tenure_months', '0').strip()
        custom_emi_str = request.form.get('monthly_emi', '').strip()
        due_day_str = request.form.get('emi_due_day', '5').strip()
        start_date_str = request.form.get('start_date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not loan_name or not lender_name or not principal_str or not tenure_str or not start_date_str:
            flash('Please fill in all mandatory loan details.', 'danger')
            return render_template('loans.html', show_add_form=True, loan_types=LOAN_TYPES)

        try:
            principal = Decimal(principal_str)
            rate = Decimal(rate_str) if rate_str else Decimal('0.00')
            tenure = int(tenure_str)
            due_day = int(due_day_str)
            start_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except (ValueError, InvalidOperation):
            flash('Invalid numeric or date format entered.', 'danger')
            return render_template('loans.html', show_add_form=True, loan_types=LOAN_TYPES)

        # Calculate or accept lender EMI
        calc_res = calculate_emi(principal, rate, tenure)
        if custom_emi_str:
            try:
                monthly_emi = round_curr(Decimal(custom_emi_str))
                tot_payable = round_curr(monthly_emi * tenure)
            except Exception:
                monthly_emi = calc_res['monthly_emi']
                tot_payable = calc_res['total_payable']
        else:
            monthly_emi = calc_res['monthly_emi']
            tot_payable = calc_res['total_payable']

        # Auto-generate unique Loan ID Code
        loan_count = Loan.query.count() + 1
        year_mo = start_d.strftime('%Y%m')
        code = f"LN-{year_mo}-{loan_count:04d}"

        # End date estimate
        end_d = start_d + timedelta(days=tenure * 30)

        loan = Loan(
            user_id=current_user.id,
            loan_id_code=code,
            loan_name=loan_name,
            loan_type=loan_type,
            lender_name=lender_name,
            loan_reference_number=reference_no,
            principal_amount=principal,
            annual_interest_rate=rate,
            start_date=start_d,
            end_date=end_d,
            tenure_months=tenure,
            monthly_emi=monthly_emi,
            emi_due_day=due_day,
            total_amount_payable=tot_payable,
            next_emi_date=start_d,
            status='active',
            notes=notes
        )
        db.session.add(loan)
        db.session.flush()

        # Generate full EMI schedule
        generate_loan_emi_schedule(loan, current_user.id)

        # Audit
        audit = AuditLog(
            user_id=current_user.id,
            action='LOAN_CREATED',
            entity_type='Loan',
            entity_id=loan.id,
            details=f"Created Loan '{loan.loan_name}' ({loan.loan_id_code}) of ₹{principal:,.2f}.",
            ip_address=get_client_ip()
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Loan '{loan.loan_name}' added and EMI schedule generated successfully!", 'success')
        return redirect(url_for('loan_details', id=loan.id))

    return render_template('loans.html', show_add_form=True, loan_types=LOAN_TYPES)


@app.route('/loans/<int:id>')
@login_required
def loan_details(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    schedules = loan.emi_schedules.all()
    payments = loan.payments.all()
    return render_template('loan_details.html', loan=loan, schedules=schedules, payments=payments)


@app.route('/loans/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        loan.loan_name = request.form.get('loan_name', '').strip()
        loan.loan_type = request.form.get('loan_type', '').strip()
        loan.lender_name = request.form.get('lender_name', '').strip()
        loan.loan_reference_number = request.form.get('loan_reference_number', '').strip()
        loan.status = request.form.get('status', 'active').strip()
        loan.notes = request.form.get('notes', '').strip()

        db.session.commit()
        flash('Loan details updated.', 'success')
        return redirect(url_for('loan_details', id=loan.id))

    return render_template('loan_details.html', loan=loan, edit_mode=True, loan_types=LOAN_TYPES, loan_statuses=LOAN_STATUSES)


@app.route('/loans/<int:id>/delete', methods=['POST'])
@login_required
def delete_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = loan.loan_name
    db.session.delete(loan)
    db.session.commit()
    flash(f"Loan '{name}' and associated schedules were deleted.", 'info')
    return redirect(url_for('loans_list'))


@app.route('/loans/<int:id>/close', methods=['POST'])
@login_required
def close_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    loan.status = 'closed'
    db.session.commit()
    flash(f"Loan '{loan.loan_name}' is now marked as Closed.", 'success')
    return redirect(url_for('loan_details', id=loan.id))


# ─── EMI CALCULATOR ──────────────────────────────────────────

@app.route('/emi-calculator', methods=['GET', 'POST'])
@login_required
def emi_calculator():
    result = None
    principal = 500000
    rate = 10.5
    tenure = 24

    if request.method == 'POST':
        try:
            principal = float(request.form.get('principal', 500000))
            rate = float(request.form.get('interest_rate', 10.5))
            tenure = int(request.form.get('tenure_months', 24))
            result = calculate_emi(principal, rate, tenure)
        except Exception as e:
            flash(f"Calculation error: {e}", 'danger')

    return render_template(
        'emi_calculator.html',
        result=result,
        principal=principal,
        rate=rate,
        tenure=tenure
    )


# ─── EMI SCHEDULE MANAGEMENT ─────────────────────────────────

@app.route('/emi-schedule')
@login_required
def emi_schedule():
    uid = current_user.id
    update_all_emi_statuses(uid)

    loan_id = request.args.get('loan_id', type=int)
    status = request.args.get('status', '').strip()
    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()

    user_loans = Loan.query.filter_by(user_id=uid).all()

    query = EMISchedule.query.filter_by(user_id=uid)
    if loan_id:
        query = query.filter_by(loan_id=loan_id)
    if status:
        query = query.filter_by(status=status)
    if month and year:
        try:
            m = int(month)
            y = int(year)
            query = query.filter(
                db.extract('month', EMISchedule.due_date) == m,
                db.extract('year', EMISchedule.due_date) == y
            )
        except ValueError:
            pass

    schedules = query.order_by(EMISchedule.due_date.asc()).all()

    return render_template(
        'emi_schedule.html',
        schedules=schedules,
        loans=user_loans,
        current_loan_id=loan_id,
        current_status=status,
        current_month=month,
        current_year=year
    )


@app.route('/emi/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_emi_schedule_item(id):
    emi = EMISchedule.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        try:
            new_amount = Decimal(request.form.get('scheduled_amount', str(emi.scheduled_amount)))
            due_str = request.form.get('due_date', '').strip()
            notes = request.form.get('notes', '').strip()

            emi.scheduled_amount = round_curr(new_amount)
            emi.remaining_amount = max(Decimal('0.00'), round_curr(emi.scheduled_amount - emi.amount_paid))
            if due_str:
                emi.due_date = datetime.strptime(due_str, '%Y-%m-%d').date()
            emi.notes = notes

            # Re-evaluate status
            if emi.remaining_amount == 0 and emi.amount_paid > 0:
                emi.status = 'paid'
            elif emi.amount_paid > 0:
                emi.status = 'partially_paid'

            db.session.commit()
            flash('Installment schedule updated.', 'success')
        except Exception as e:
            flash(f"Update error: {e}", 'danger')

        return redirect(url_for('emi_schedule', loan_id=emi.loan_id))

    return render_template('emi_schedule.html', edit_item=emi)


# ─── LOAN PAYMENT MANAGEMENT ROUTES ──────────────────────────

@app.route('/loan-payments')
@login_required
def loan_payments():
    uid = current_user.id
    loans = Loan.query.filter_by(user_id=uid).all()
    payments = LoanPayment.query.filter_by(user_id=uid).order_by(LoanPayment.payment_date.desc()).all()
    return render_template('loan_payments.html', loans=loans, payments=payments, payment_methods=PAYMENT_METHODS)


@app.route('/loan-payments/record', methods=['POST'])
@login_required
def record_general_payment():
    loan_id = request.form.get('loan_id', type=int)
    amount_str = request.form.get('amount', '0').strip()
    payment_date_str = request.form.get('payment_date', '').strip()
    payment_method = request.form.get('payment_method', 'Bank Transfer')
    transaction_ref = request.form.get('transaction_reference', '').strip()
    notes = request.form.get('notes', '').strip()

    if not loan_id or not amount_str or not payment_date_str:
        flash('Loan, amount, and payment date are required.', 'danger')
        return redirect(url_for('loan_payments'))

    try:
        amount = Decimal(amount_str)
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
    except Exception:
        flash('Invalid amount or date format.', 'danger')
        return redirect(url_for('loan_payments'))

    # Optional receipt attachment
    receipt_filename = None
    if 'receipt_file' in request.files and request.files['receipt_file'].filename:
        file = request.files['receipt_file']
        errors = validate_uploaded_file(file)
        if not errors:
            receipt_filename = save_receipt_file(file, current_user.id)

    payment, err = record_general_loan_payment(
        loan_id=loan_id,
        user_id=current_user.id,
        amount=amount,
        payment_date=payment_date,
        payment_method=payment_method,
        transaction_ref=transaction_ref,
        notes=notes,
        receipt_filename=receipt_filename,
        ip_address=get_client_ip()
    )

    if err:
        flash(err, 'danger')
    else:
        flash(f"Payment of ₹{amount:,.2f} recorded! Receipt: {payment.receipt.receipt_number}", 'success')

    return redirect(url_for('loan_payments'))


# ─── EMI PAYMENT MANAGEMENT ROUTES ───────────────────────────

@app.route('/emi-payments')
@login_required
def emi_payments():
    uid = current_user.id
    update_all_emi_statuses(uid)

    unpaid_emis = EMISchedule.query.filter(
        EMISchedule.user_id == uid,
        EMISchedule.status.in_(['due_today', 'overdue', 'partially_paid', 'upcoming'])
    ).order_by(EMISchedule.due_date.asc()).all()

    return render_template('emi_payments.html', emis=unpaid_emis, payment_methods=PAYMENT_METHODS)


@app.route('/emi/<int:id>/pay', methods=['GET', 'POST'])
@login_required
def pay_emi(id):
    emi = EMISchedule.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        amount_str = request.form.get('amount', str(emi.remaining_amount)).strip()
        date_str = request.form.get('payment_date', '').strip()
        method = request.form.get('payment_method', 'UPI').strip()
        tx_ref = request.form.get('transaction_reference', '').strip()
        notes = request.form.get('notes', '').strip()

        try:
            amt = Decimal(amount_str)
            p_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        except Exception:
            flash('Invalid payment amount or date.', 'danger')
            return redirect(url_for('emi_payments'))

        receipt_filename = None
        if 'receipt_file' in request.files and request.files['receipt_file'].filename:
            file = request.files['receipt_file']
            errors = validate_uploaded_file(file)
            if not errors:
                receipt_filename = save_receipt_file(file, current_user.id)

        payment, err = record_emi_payment(
            emi_id=emi.id,
            user_id=current_user.id,
            amount_paying=amt,
            payment_date=p_date,
            payment_method=method,
            transaction_ref=tx_ref,
            notes=notes,
            receipt_filename=receipt_filename,
            ip_address=get_client_ip()
        )

        if err:
            flash(err, 'danger')
        else:
            flash(f"Payment of ₹{amt:,.2f} recorded! Generated Receipt #{payment.receipt.receipt_number}", 'success')
            return redirect(url_for('view_receipt', id=payment.receipt.id))

    return render_template('emi_payments.html', selected_emi=emi, payment_methods=PAYMENT_METHODS)


# ─── PAYMENT RECEIPTS & HISTORY ──────────────────────────────

@app.route('/payment-history')
@login_required
def payment_history():
    uid = current_user.id
    loan_id = request.args.get('loan_id', type=int)
    method = request.args.get('method', '').strip()
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    loans = Loan.query.filter_by(user_id=uid).all()

    query = LoanPayment.query.filter_by(user_id=uid)
    if loan_id:
        query = query.filter_by(loan_id=loan_id)
    if method:
        query = query.filter_by(payment_method=method)
    if status:
        query = query.filter_by(payment_status=status)
    if search:
        query = query.filter(
            (LoanPayment.payment_reference.ilike(f'%{search}%')) |
            (LoanPayment.transaction_reference.ilike(f'%{search}%'))
        )

    payments = query.order_by(LoanPayment.payment_date.desc(), LoanPayment.created_at.desc()).all()
    tot_eligible = sum(p.amount for p in payments if p.payment_status == 'completed')

    return render_template(
        'payment_history.html',
        payments=payments,
        loans=loans,
        payment_methods=PAYMENT_METHODS,
        payment_statuses=PAYMENT_STATUSES,
        current_loan_id=loan_id,
        current_method=method,
        current_status=status,
        search=search,
        total_eligible=tot_eligible
    )


@app.route('/receipts/<int:id>')
@login_required
def view_receipt(id):
    receipt = PaymentReceipt.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('payment_history.html', receipt=receipt, view_receipt_modal=True)


@app.route('/receipts/<int:id>/pdf')
@login_required
def download_receipt_pdf(id):
    receipt = PaymentReceipt.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    pdf_bytes = generate_payment_receipt_pdf(receipt)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={receipt.receipt_number}.pdf'}
    )


@app.route('/payments/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_payment(id):
    reason = request.form.get('reason', 'User requested cancellation').strip()
    success, err = cancel_payment_record(
        payment_id=id,
        user_id=current_user.id,
        reason=reason,
        ip_address=get_client_ip()
    )
    if success:
        flash('Payment cancelled and balances safely recalculated.', 'warning')
    else:
        flash(err, 'danger')
    return redirect(url_for('payment_history'))


# ─── REPORTS & EXPORTS ROUTE ─────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    loans = Loan.query.filter_by(user_id=current_user.id).all()
    return render_template('reports.html', loans=loans)


@app.route('/reports/loans/pdf')
@login_required
def report_loans_pdf():
    loans = Loan.query.filter_by(user_id=current_user.id).all()
    pdf_bytes = generate_loans_summary_pdf(loans, current_user.full_name)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=Loans_Summary_{date.today().isoformat()}.pdf'}
    )


@app.route('/reports/loans/<int:id>/schedule/pdf')
@login_required
def report_loan_schedule_pdf(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    installments = loan.emi_schedules.all()
    pdf_bytes = generate_emi_schedule_pdf(loan, installments, current_user.full_name)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=Schedule_{loan.loan_id_code}.pdf'}
    )


@app.route('/reports/documents/csv')
@login_required
def report_documents_csv():
    docs = Document.query.filter_by(user_id=current_user.id).all()
    csv_data = export_documents_csv(docs)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=documents_{date.today().isoformat()}.csv'}
    )


@app.route('/reports/loans/csv')
@login_required
def report_loans_csv():
    loans = Loan.query.filter_by(user_id=current_user.id).all()
    csv_data = export_loans_csv(loans)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=loans_{date.today().isoformat()}.csv'}
    )


@app.route('/reports/payments/csv')
@login_required
def report_payments_csv():
    payments = LoanPayment.query.filter_by(user_id=current_user.id).order_by(LoanPayment.payment_date.desc()).all()
    csv_data = export_payments_csv(payments)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=payment_history_{date.today().isoformat()}.csv'}
    )


# ─── NOTIFICATIONS ROUTE ─────────────────────────────────────

@app.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '').strip()
    unread_only = request.args.get('unread', '').strip() == '1'

    query = Notification.query.filter_by(user_id=current_user.id)
    if category:
        query = query.filter_by(category=category)
    if unread_only:
        query = query.filter_by(is_read=False)

    notifications_list = query.order_by(Notification.created_at.desc()).all()
    return render_template(
        'notifications.html',
        notifications=notifications_list,
        current_category=category,
        unread_only=unread_only
    )


@app.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def mark_notification_read(id):
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(url_for('notifications'))


@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))


@app.route('/notifications/<int:id>/delete', methods=['POST'])
@login_required
def delete_notification(id):
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    flash('Notification dismissed.', 'info')
    return redirect(url_for('notifications'))


# ─── GLOBAL SEARCH ROUTE ─────────────────────────────────────

@app.route('/search')
@login_required
def global_search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('dashboard'))

    uid = current_user.id

    docs = Document.query.filter(
        Document.user_id == uid,
        (Document.title.ilike(f'%{q}%')) |
        (Document.document_number.ilike(f'%{q}%')) |
        (Document.holder_name.ilike(f'%{q}%')) |
        (Document.issuing_authority.ilike(f'%{q}%'))
    ).all()

    loans = Loan.query.filter(
        Loan.user_id == uid,
        (Loan.loan_name.ilike(f'%{q}%')) |
        (Loan.lender_name.ilike(f'%{q}%')) |
        (Loan.loan_id_code.ilike(f'%{q}%')) |
        (Loan.loan_reference_number.ilike(f'%{q}%'))
    ).all()

    payments = LoanPayment.query.filter(
        LoanPayment.user_id == uid,
        (LoanPayment.payment_reference.ilike(f'%{q}%')) |
        (LoanPayment.transaction_reference.ilike(f'%{q}%'))
    ).all()

    emis = EMISchedule.query.join(Loan).filter(
        EMISchedule.user_id == uid,
        (Loan.loan_name.ilike(f'%{q}%'))
    ).all()

    return render_template(
        'search.html',
        query=q,
        documents=docs,
        loans=loans,
        payments=payments,
        emis=emis
    )


# ─── SETTINGS & REMINDER PREFERENCES ─────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    pref = current_user.reminder_preference
    if not pref:
        pref = UserReminderPreference(
            user_id=current_user.id,
            doc_days_before='30,14,7,1',
            emi_days_before='7,3,1,0',
            in_app_enabled=True,
            email_enabled=False
        )
        db.session.add(pref)
        db.session.commit()

    if request.method == 'POST':
        doc_days = request.form.get('doc_days', '30,14,7,1').strip()
        emi_days = request.form.get('emi_days', '7,3,1,0').strip()
        in_app = request.form.get('in_app_enabled') == 'on'

        pref.doc_days_before = doc_days
        pref.emi_days_before = emi_days
        pref.in_app_enabled = in_app
        db.session.commit()

        flash('Reminder preferences saved successfully.', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', pref=pref, tesseract_cmd=Config.TESSERACT_CMD)



# ─── GOVERNMENT SERVICES & APPLICATION TRACKING ───────────────

GOVERNMENT_SERVICES = [
    {
        'name': 'Income Certificate',
        'description': 'Track an income certificate application.',
        'portal': 'https://aaplesarkar.mahaonline.gov.in/'
    },
    {
        'name': 'Domicile Certificate',
        'description': 'Track a domicile certificate application.',
        'portal': 'https://aaplesarkar.mahaonline.gov.in/'
    },
    {
        'name': 'Caste Certificate',
        'description': 'Track a caste certificate application.',
        'portal': 'https://aaplesarkar.mahaonline.gov.in/'
    },
    {
        'name': 'Non-Creamy Layer Certificate',
        'description': 'Track a non-creamy layer certificate application.',
        'portal': 'https://aaplesarkar.mahaonline.gov.in/'
    },
    {
        'name': 'Other Government Document',
        'description': 'Track another certificate or government document.',
        'portal': 'https://aaplesarkar.mahaonline.gov.in/'
    },
]

GOVERNMENT_APPLICATION_STATUSES = {
    'draft': 'Draft',
    'submitted_by_user': 'Submitted (user reported)',
    'in_progress': 'In Progress (not verified)',
    'completed': 'Completed (not verified)',
    'rejected': 'Rejected (not verified)',
    'cancelled': 'Cancelled',
}


@app.route('/government-services', methods=['GET', 'POST'])
@login_required
def government_services():
    """Save and locally track government document applications.

    This page does not submit applications to a government portal or verify
    status with a government department. Users must apply on the official site.
    """
    if request.method == 'POST':
        service_type = request.form.get('service_type', '').strip()
        applicant_name = request.form.get('applicant_name', '').strip()
        district = request.form.get('district', '').strip()
        application_date_str = request.form.get('application_date', '').strip()
        expected_date_str = request.form.get('expected_completion_date', '').strip()
        official_reference = request.form.get('official_reference', '').strip()
        notes = request.form.get('notes', '').strip()

        allowed_services = {item['name'] for item in GOVERNMENT_SERVICES}
        if service_type not in allowed_services:
            flash('Please select a valid government service.', 'danger')
            return redirect(url_for('government_services'))

        if not applicant_name or not district:
            flash('Applicant name and district are required.', 'danger')
            return redirect(url_for('government_services'))

        try:
            application_date = (
                datetime.strptime(application_date_str, '%Y-%m-%d').date()
                if application_date_str else None
            )
            expected_date = (
                datetime.strptime(expected_date_str, '%Y-%m-%d').date()
                if expected_date_str else None
            )
        except ValueError:
            flash('Please enter valid application dates.', 'danger')
            return redirect(url_for('government_services'))

        if application_date and expected_date and expected_date < application_date:
            flash('Expected completion date cannot be before the application date.', 'danger')
            return redirect(url_for('government_services'))

        application = GovernmentApplication(
            user_id=current_user.id,
            service_type=service_type,
            applicant_name=applicant_name,
            district=district,
            status='draft',
            official_reference=official_reference or None,
            application_date=application_date,
            expected_completion_date=expected_date,
            notes=notes or None,
        )
        db.session.add(application)
        db.session.flush()

        db.session.add(AuditLog(
            user_id=current_user.id,
            action='GOVERNMENT_APPLICATION_CREATED',
            entity_type='GovernmentApplication',
            entity_id=application.id,
            details=f'Created local tracker for {service_type}.',
            ip_address=get_client_ip()
        ))
        db.session.commit()
        flash('Application tracking record saved. Apply through the official portal separately.', 'success')
        return redirect(url_for('government_services'))

    applications = GovernmentApplication.query.filter_by(
        user_id=current_user.id
    ).order_by(GovernmentApplication.created_at.desc()).all()

    # Render inline so this feature works without requiring a new template file.
    from flask import render_template_string
    page = r"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Government Services | Smart Document Manager</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body{background:#f4f7fb;color:#172033;font-family:Arial,sans-serif}
        .wrap{max-width:1100px;margin:32px auto;padding:0 16px}
        .panel{background:#fff;border:1px solid #e5eaf2;border-radius:16px;padding:24px;margin-bottom:22px;box-shadow:0 6px 24px #1720330a}
        .muted{color:#65728a}.btn-primary{background:#174ea6;border-color:#174ea6}
        .table td,.table th{vertical-align:middle}
      </style>
    </head>
    <body>
    <main class="wrap">
      <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div><h1 class="h3 mb-1">Government Services & Applications</h1>
        <p class="muted mb-0">Save application details and track your own records.</p></div>
        <a class="btn btn-outline-primary" href="{{ portal }}" target="_blank" rel="noopener noreferrer">Open Aaple Sarkar Portal ↗</a>
      </div>
      <div class="alert alert-warning">
        <strong>Important:</strong> This module only stores records in your account.
        It does not submit forms to a government department or verify application status.
        Use the official portal for actual submission and confirmation.
      </div>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
          <div class="alert alert-{{ 'danger' if category == 'error' else category }}">{{ message }}</div>
        {% endfor %}
      {% endwith %}
      <section class="panel">
        <h2 class="h5 mb-3">Add application tracker</h2>
        <form method="post" action="{{ url_for('government_services') }}">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="service_type">Document / service *</label>
              <select class="form-select" id="service_type" name="service_type" required>
                <option value="">Choose service</option>
                {% for item in services %}<option value="{{ item.name }}">{{ item.name }}</option>{% endfor %}
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="applicant_name">Applicant full name *</label>
              <input class="form-control" id="applicant_name" name="applicant_name" maxlength="150" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="district">District *</label>
              <input class="form-control" id="district" name="district" maxlength="100" placeholder="e.g. Raigad" required>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="official_reference">Official application / acknowledgement number</label>
              <input class="form-control" id="official_reference" name="official_reference" maxlength="100">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="application_date">Application date</label>
              <input class="form-control" type="date" id="application_date" name="application_date">
            </div>
            <div class="col-md-6">
              <label class="form-label" for="expected_completion_date">Expected completion date</label>
              <input class="form-control" type="date" id="expected_completion_date" name="expected_completion_date">
            </div>
            <div class="col-12">
              <label class="form-label" for="notes">Notes</label>
              <textarea class="form-control" id="notes" name="notes" rows="3" maxlength="4000"></textarea>
            </div>
          </div>
          <button class="btn btn-primary mt-3" type="submit">Save tracker</button>
        </form>
      </section>
      <section class="panel">
        <h2 class="h5 mb-3">My application records</h2>
        {% if applications %}
        <div class="table-responsive"><table class="table table-hover">
          <thead><tr><th>Service</th><th>Applicant</th><th>District</th><th>Reference</th><th>Application date</th><th>Status</th><th>Notes</th></tr></thead>
          <tbody>{% for a in applications %}
            <tr>
              <td>{{ a.service_type }}</td><td>{{ a.applicant_name }}</td><td>{{ a.district }}</td>
              <td>{{ a.official_reference or '—' }}</td>
              <td>{{ a.application_date.strftime('%d %b %Y') if a.application_date else '—' }}</td>
              <td>
                <span class="badge text-bg-secondary">{{ a.status_display }}</span>
                <form class="mt-2" method="post" action="{{ url_for('update_government_application_status', application_id=a.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <select class="form-select form-select-sm mb-1" name="status" aria-label="Local tracking status">
                    {% for key, label in statuses.items() %}
                    <option value="{{ key }}" {% if a.status == key %}selected{% endif %}>{{ label }}</option>
                    {% endfor %}
                  </select>
                  <button class="btn btn-sm btn-outline-secondary" type="submit">Update local status</button>
                </form>
              </td>
              <td>{{ a.notes or '—' }}</td>
            </tr>
          {% endfor %}</tbody>
        </table></div>
        {% else %}<p class="muted mb-0">No application trackers saved yet.</p>{% endif %}
      </section>
      <p><a href="{{ url_for('dashboard') }}">← Back to dashboard</a></p>
    </main>
    </body></html>
    """
    return render_template_string(
        page,
        applications=applications,
        services=GOVERNMENT_SERVICES,
        statuses=GOVERNMENT_APPLICATION_STATUSES,
        portal='https://aaplesarkar.mahaonline.gov.in/',
        csrf_token=generate_csrf
    )


@app.route('/government-applications/<int:application_id>/status', methods=['POST'])
@login_required
def update_government_application_status(application_id):
    """Update the user's local status note; this is not an official status check."""
    application = GovernmentApplication.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first_or_404()

    status = request.form.get('status', '').strip()
    if status not in GOVERNMENT_APPLICATION_STATUSES:
        flash('Invalid application status.', 'danger')
        return redirect(url_for('government_services'))

    application.status = status
    reference = request.form.get('official_reference', '').strip()
    if reference:
        application.official_reference = reference[:100]

    db.session.add(AuditLog(
        user_id=current_user.id,
        action='GOVERNMENT_APPLICATION_STATUS_UPDATED',
        entity_type='GovernmentApplication',
        entity_id=application.id,
        details=f'Local status set to {status}; not verified with government.',
        ip_address=get_client_ip()
    ))
    db.session.commit()
    flash('Local tracking status updated. It has not been verified with a government system.', 'info')
    return redirect(url_for('government_services'))


# ─── ERROR HANDLERS ──────────────────────────────────────────

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    import sys
    port = int(os.environ.get('PORT', 5000))
    use_ssl = '--https' in sys.argv or os.environ.get('USE_SSL', '').lower() in ('1', 'true', 'yes')

    if use_ssl:
        # Creates a local development certificate; use trusted HTTPS in production.
        try:
            from werkzeug.serving import make_ssl_devcert
            cert_dir = os.path.join(app.root_path, 'instance', 'dev_https_cert')
            os.makedirs(cert_dir, exist_ok=True)
            cert_base = os.path.join(cert_dir, 'localhost')
            cert_path, key_path = make_ssl_devcert(cert_base, host='localhost')
            local_ip = 'your-computer-local-IP'
            try:
                import socket
                local_ip = socket.gethostbyname(socket.gethostname())
            except OSError:
                pass
            print('=' * 65)
            print(' HTTPS development mode enabled for camera testing.')
            print(f' Laptop: https://localhost:{port}')
            print(f' Phone:  https://{local_ip}:{port}')
            print(' A local certificate warning may appear; development use only.')
            print('=' * 65)
            app.run(host='0.0.0.0', port=port, ssl_context=(cert_path, key_path), debug=False)
        except Exception as exc:
            print('Could not start HTTPS mode:', exc)
            print('Try: python -m pip install cryptography')
            raise
    else:
        print(f'Open http://127.0.0.1:{port} on this computer for camera access.')
        print('For phone/LAN live camera, run: python app.py --https')
        app.run(host='0.0.0.0', port=port, debug=False)
