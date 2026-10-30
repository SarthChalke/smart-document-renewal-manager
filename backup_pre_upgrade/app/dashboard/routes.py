"""Dashboard routes."""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
from app import db
from app.models import (Document, Loan, EMIPayment, Notification,
                        DOCUMENT_CATEGORY_DICT, LOAN_TYPE_DICT)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    thirty_days = today + timedelta(days=30)

    # ── Document stats ──
    total_docs = Document.query.filter_by(user_id=current_user.id).count()
    docs_with_expiry = Document.query.filter(
        Document.user_id == current_user.id,
        Document.expiry_date.isnot(None)
    ).all()

    valid_docs = sum(1 for d in docs_with_expiry if d.expiry_status == 'valid')
    expiring_docs = sum(1 for d in docs_with_expiry if d.expiry_status == 'expiring_soon')
    expired_docs = sum(1 for d in docs_with_expiry if d.expiry_status == 'expired')

    # ── Loan stats ──
    total_loans = Loan.query.filter_by(user_id=current_user.id).count()
    active_loans = Loan.query.filter_by(user_id=current_user.id, status='active').count()
    monthly_emi = db.session.query(func.sum(Loan.monthly_emi)).filter(
        Loan.user_id == current_user.id, Loan.status == 'active'
    ).scalar() or 0

    # Outstanding estimate
    active_loan_objects = Loan.query.filter_by(user_id=current_user.id, status='active').all()
    outstanding = None
    has_data = False
    outstanding_total = 0
    for loan in active_loan_objects:
        est = loan.outstanding_estimate
        if est is not None:
            outstanding_total += est
            has_data = True
    if has_data:
        outstanding = outstanding_total

    # ── EMI stats ──
    user_loan_ids = [l.id for l in Loan.query.filter_by(user_id=current_user.id).all()]

    upcoming_emis = 0
    due_today_emis = 0
    overdue_emis = 0
    paid_this_month = 0

    if user_loan_ids:
        upcoming_emis = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'upcoming',
            EMIPayment.due_date > today,
            EMIPayment.due_date <= thirty_days
        ).count()

        due_today_emis = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.due_date == today,
            EMIPayment.status != 'paid'
        ).count()

        overdue_emis = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'overdue'
        ).count()

        month_start = today.replace(day=1)
        paid_this_month = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'paid',
            EMIPayment.payment_date >= month_start,
            EMIPayment.payment_date <= today
        ).count()

    # ── Upcoming document expiries ──
    upcoming_doc_expiries = Document.query.filter(
        Document.user_id == current_user.id,
        Document.expiry_date.isnot(None),
        Document.expiry_date >= today,
        Document.expiry_date <= thirty_days
    ).order_by(Document.expiry_date.asc()).limit(5).all()

    # ── Expired documents ──
    expired_doc_list = Document.query.filter(
        Document.user_id == current_user.id,
        Document.expiry_date.isnot(None),
        Document.expiry_date < today
    ).order_by(Document.expiry_date.desc()).limit(5).all()

    # ── Upcoming loan payments ──
    upcoming_loan_payments = []
    if user_loan_ids:
        upcoming_loan_payments = db.session.query(EMIPayment, Loan).join(
            Loan, EMIPayment.loan_id == Loan.id
        ).filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status.in_(['upcoming', 'due_today']),
            EMIPayment.due_date >= today,
            EMIPayment.due_date <= thirty_days
        ).order_by(EMIPayment.due_date.asc()).limit(5).all()

    # ── Overdue EMIs ──
    overdue_emi_list = []
    if user_loan_ids:
        overdue_emi_list = db.session.query(EMIPayment, Loan).join(
            Loan, EMIPayment.loan_id == Loan.id
        ).filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'overdue'
        ).order_by(EMIPayment.due_date.asc()).limit(5).all()

    # ── Recent uploads ──
    recent_uploads = Document.query.filter_by(user_id=current_user.id) \
        .order_by(Document.uploaded_at.desc()).limit(5).all()

    # ── Recent payments ──
    recent_payments = []
    if user_loan_ids:
        recent_payments = db.session.query(EMIPayment, Loan).join(
            Loan, EMIPayment.loan_id == Loan.id
        ).filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'paid'
        ).order_by(EMIPayment.payment_date.desc()).limit(5).all()

    # ── Recent notifications ──
    recent_notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('dashboard/index.html',
                           today=today,
                           total_docs=total_docs,
                           valid_docs=valid_docs,
                           expiring_docs=expiring_docs,
                           expired_docs=expired_docs,
                           total_loans=total_loans,
                           active_loans=active_loans,
                           monthly_emi=float(monthly_emi),
                           outstanding=outstanding,
                           upcoming_emis=upcoming_emis,
                           due_today_emis=due_today_emis,
                           overdue_emis=overdue_emis,
                           paid_this_month=paid_this_month,
                           upcoming_doc_expiries=upcoming_doc_expiries,
                           expired_doc_list=expired_doc_list,
                           upcoming_loan_payments=upcoming_loan_payments,
                           overdue_emi_list=overdue_emi_list,
                           recent_uploads=recent_uploads,
                           recent_payments=recent_payments,
                           recent_notifications=recent_notifications)


@dashboard_bp.route('/api/chart-data')
@login_required
def chart_data():
    """API endpoint for dashboard chart data."""
    today = date.today()
    user_id = current_user.id

    # Documents by category
    docs = Document.query.filter_by(user_id=user_id).all()
    cat_counts = {}
    for d in docs:
        label = DOCUMENT_CATEGORY_DICT.get(d.category, d.category)
        cat_counts[label] = cat_counts.get(label, 0) + 1

    # Documents by expiry status
    status_counts = {'Valid': 0, 'Expiring Soon': 0, 'Expired': 0, 'No Expiry': 0}
    for d in docs:
        s = d.expiry_status
        if s == 'valid':
            status_counts['Valid'] += 1
        elif s == 'expiring_soon':
            status_counts['Expiring Soon'] += 1
        elif s == 'expired':
            status_counts['Expired'] += 1
        else:
            status_counts['No Expiry'] += 1

    # Loan distribution
    loans = Loan.query.filter_by(user_id=user_id).all()
    loan_dist = {}
    for l in loans:
        label = LOAN_TYPE_DICT.get(l.loan_type, l.loan_type)
        loan_dist[label] = loan_dist.get(label, 0) + 1

    # Monthly EMI payments (last 6 months)
    user_loan_ids = [l.id for l in loans]
    monthly_payments = {}
    if user_loan_ids:
        for i in range(5, -1, -1):
            m_date = today.replace(day=1) - timedelta(days=i * 30)
            month_key = m_date.strftime('%b %Y')
            m_start = m_date.replace(day=1)
            if m_date.month == 12:
                m_end = m_date.replace(year=m_date.year + 1, month=1, day=1)
            else:
                m_end = m_date.replace(month=m_date.month + 1, day=1)

            paid_count = EMIPayment.query.filter(
                EMIPayment.loan_id.in_(user_loan_ids),
                EMIPayment.status == 'paid',
                EMIPayment.payment_date >= m_start,
                EMIPayment.payment_date < m_end
            ).count()
            monthly_payments[month_key] = paid_count

    # Paid vs Pending
    paid_total = 0
    pending_total = 0
    if user_loan_ids:
        paid_total = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'paid'
        ).count()
        pending_total = EMIPayment.query.filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status != 'paid'
        ).count()

    return jsonify({
        'doc_categories': cat_counts,
        'doc_status': status_counts,
        'loan_distribution': loan_dist,
        'monthly_payments': monthly_payments,
        'paid_vs_pending': {'Paid': paid_total, 'Pending': pending_total}
    })
