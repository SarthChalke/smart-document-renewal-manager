"""Dashboard routes."""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
from app import db
from app.models import Document, DocumentRenewal, Loan, LoanPayment, Notification, EMISchedule

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    uid = current_user.id
    today = date.today()
    thirty_days = today + timedelta(days=30)

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
    total_loan_amount = sum(float(l.principal_amount) for l in user_loans)
    total_eligible_paid = sum(float(l.total_eligible_paid) for l in user_loans)
    total_outstanding_principal = sum(float(l.estimated_outstanding_principal) for l in user_loans if l.status == 'active')
    total_monthly_emi = sum(float(l.monthly_emi) for l in user_loans if l.status == 'active')

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

    unread_count = Notification.query.filter_by(
        user_id=uid, is_read=False
    ).count()

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
        unread_count=unread_count,
        user_loans=user_loans
    )


@dashboard_bp.route('/api/dashboard-charts')
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

        total_paid_in_month = db.session.query(func.sum(LoanPayment.amount)).filter(
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