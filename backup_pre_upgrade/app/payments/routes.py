"""Payment history routes with CSV export."""
import csv
import io
from flask import Blueprint, render_template, request, Response, abort
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import extract
from app import db
from app.models import Loan, EMIPayment

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


@payments_bp.route('/')
@login_required
def payment_history():
    page = request.args.get('page', 1, type=int)
    loan_id = request.args.get('loan_id', '', type=str)
    status = request.args.get('status', '').strip()
    month = request.args.get('month', '', type=str)
    year = request.args.get('year', '', type=str)
    search = request.args.get('search', '').strip()

    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    user_loan_ids = [l.id for l in user_loans]

    if not user_loan_ids:
        return render_template('payments/history.html',
                               payments=None,
                               loans=user_loans,
                               current_loan_id='',
                               current_status=status,
                               current_month=month,
                               current_year=year,
                               search=search)

    query = db.session.query(EMIPayment, Loan).join(
        Loan, EMIPayment.loan_id == Loan.id
    ).filter(EMIPayment.loan_id.in_(user_loan_ids))

    if loan_id:
        query = query.filter(EMIPayment.loan_id == int(loan_id))

    if status:
        query = query.filter(EMIPayment.status == status)

    if search:
        query = query.filter(
            (Loan.loan_name.ilike(f'%{search}%')) |
            (EMIPayment.transaction_reference.ilike(f'%{search}%'))
        )

    if month and year:
        query = query.filter(
            extract('month', EMIPayment.due_date) == int(month),
            extract('year', EMIPayment.due_date) == int(year)
        )
    elif year:
        query = query.filter(extract('year', EMIPayment.due_date) == int(year))

    query = query.order_by(EMIPayment.due_date.desc())
    payments = query.paginate(page=page, per_page=15, error_out=False)

    # Monthly summary
    paid_total = 0
    pending_total = 0
    for emi, loan in query.all():
        if emi.status == 'paid':
            paid_total += float(emi.amount)
        else:
            pending_total += float(emi.amount)

    return render_template('payments/history.html',
                           payments=payments,
                           loans=user_loans,
                           current_loan_id=loan_id,
                           current_status=status,
                           current_month=month,
                           current_year=year,
                           search=search,
                           paid_total=paid_total,
                           pending_total=pending_total)


@payments_bp.route('/export')
@login_required
def export_csv():
    """Export payment history to CSV."""
    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    user_loan_ids = [l.id for l in user_loans]

    if not user_loan_ids:
        abort(404)

    loan_id = request.args.get('loan_id', '', type=str)
    status = request.args.get('status', '').strip()

    query = db.session.query(EMIPayment, Loan).join(
        Loan, EMIPayment.loan_id == Loan.id
    ).filter(EMIPayment.loan_id.in_(user_loan_ids))

    if loan_id:
        query = query.filter(EMIPayment.loan_id == int(loan_id))
    if status:
        query = query.filter(EMIPayment.status == status)

    results = query.order_by(EMIPayment.due_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Loan Name', 'Lender', 'EMI Amount', 'Due Date', 'Status',
                     'Payment Date', 'Transaction Reference', 'Notes'])

    for emi, loan in results:
        writer.writerow([
            loan.loan_name,
            loan.lender_name,
            f'{emi.amount:.2f}',
            emi.due_date.strftime('%Y-%m-%d') if emi.due_date else '',
            emi.status_display,
            emi.payment_date.strftime('%Y-%m-%d') if emi.payment_date else '',
            emi.transaction_reference or '',
            emi.notes or ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=payment_history_{date.today().isoformat()}.csv'}
    )
