"""EMI Management Routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date, timedelta
from decimal import Decimal
from app import db
from app.models import Loan, EMISchedule, LoanPayment, PAYMENT_METHODS
from app.forms import EMICalculationForm, LoanPaymentForm
from app.services.emi_service import calculate_emi, generate_loan_emi_schedule, update_all_emi_statuses

emi_bp = Blueprint('emi', __name__, url_prefix='/emi')


@emi_bp.route('/')
@login_required
def list_emi():
    uid = current_user.id
    today = date.today()
    thirty_days = today + timedelta(days=30)

    all_emis = EMISchedule.query.filter_by(user_id=uid).order_by(
        EMISchedule.due_date.asc()
    ).all()

    upcoming_emis = [e for e in all_emis if e.due_date >= today and e.status != 'paid']
    overdue_emis = [e for e in all_emis if e.status == 'overdue']

    return render_template(
        'emi/index.html',
        emis=all_emis,
        upcoming=upcoming_emis,
        overdue=overdue_emis
    )


@emi_bp.route('/calculator', methods=['GET', 'POST'])
@login_required
def calculator():
    form = EMICalculationForm()
    emi_result = None

    if form.validate_on_submit():
        emi_result = calculate_emi(
            float(form.principal_amount.data),
            float(form.interest_rate.data) / 100 / 12,
            form.loan_tenure_months.data
        )

    return render_template('emi/calculator.html', form=form, emi_result=emi_result)


@emi_bp.route('/<int:emi_id>/pay', methods=['GET', 'POST'])
@login_required
def pay_emi(emi_id):
    emi = EMISchedule.query.filter_by(id=emi_id, user_id=current_user.id).first_or_404()

    if emi.status == 'paid':
        flash('EMI is already paid.', 'info')
        return redirect(url_for('emi.list_emi'))

    form = LoanPaymentForm()
    if form.validate_on_submit():
        payment = LoanPayment(
            user_id=current_user.id,
            loan_id=emi.loan_id,
            amount=form.amount.data,
            payment_date=form.payment_date.data or date.today(),
            payment_method=form.payment_method.data,
            payment_status='completed'
        )
        db.session.add(payment)

        # Update EMI status
        emi.status = 'paid'
        emi.payment_date = form.payment_date.data or date.today()
        emi.paid_amount = form.amount.data

        db.session.commit()

        flash('EMI payment recorded!', 'success')
        return redirect(url_for('emi.list_emi'))

    return render_template('emi/pay.html', form=form, emi=emi)


@emi_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_emi(id):
    emi = EMISchedule.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        emi.status = request.form.get('status', emi.status)
        if request.form.get('payment_date'):
            from datetime import datetime
            emi.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
        if request.form.get('paid_amount'):
            emi.paid_amount = Decimal(request.form.get('paid_amount'))
        db.session.commit()
        flash('EMI updated.', 'success')
        return redirect(url_for('emi.list_emi'))

    statuses = ['unpaid', 'pending', 'paid', 'overdue', 'upcoming']
    return render_template('emi/edit.html', emi=emi, statuses=statuses)