"""Loan Management Routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from decimal import Decimal
from app import db
from app.models import Loan, LOAN_TYPES, LOAN_STATUSES, Document
from app.forms import LoanForm

loans_bp = Blueprint('loans', __name__, url_prefix='/loans')


@loans_bp.route('/')
@login_required
def list_loans():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    loan_type = request.args.get('loan_type', '').strip()
    status = request.args.get('status', '').strip()

    query = Loan.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            (Loan.loan_type.ilike(f'%{search}%'))
        )

    if loan_type:
        query = query.filter_by(loan_type=loan_type)

    if status:
        query = query.filter_by(status=status)

    loans = query.order_by(Loan.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'loans/index.html',
        loans=loans,
        loan_types=[t[0] for t in LOAN_TYPES],
        current_type=loan_type,
        current_status=status,
        search=search
    )


@loans_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_loan():
    form = LoanForm()
    if form.validate_on_submit():
        loan = Loan(
            user_id=current_user.id,
            loan_type=form.loan_type.data,
            principal_amount=form.principal_amount.data,
            interest_rate=form.interest_rate.data or 0,
            loan_tenure_months=form.loan_tenure_months.data,
            start_date=form.start_date.data or date.today()
        )

        # Calculate EMI
        if loan.interest_rate and loan.interest_rate > 0:
            monthly_rate = float(loan.interest_rate) / 100 / 12
            n = loan.loan_tenure_months
            p = float(loan.principal_amount)
            loan.monthly_emi = Decimal(str(p * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)))
            loan.total_amount_payable = Decimal(str(p + (loan.monthly_emi * n)))
            loan.estimated_outstanding_principal = loan.principal_amount

        db.session.add(loan)
        db.session.commit()

        flash('Loan added successfully!', 'success')
        return redirect(url_for('loans.list_loans'))

    return render_template('loans/add.html', form=form, loan_types=LOAN_TYPES)


@loans_bp.route('/<int:id>')
@login_required
def loan_details(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('loans/details.html', loan=loan)


@loans_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = LoanForm(obj=loan)

    if form.validate_on_submit():
        loan.loan_type = form.loan_type.data
        loan.principal_amount = form.principal_amount.data
        loan.interest_rate = form.interest_rate.data or 0
        loan.loan_tenure_months = form.loan_tenure_months.data
        db.session.commit()
        flash('Loan updated.', 'success')
        return redirect(url_for('loans.loan_details', id=loan.id))

    return render_template('loans/edit.html', form=form, loan=loan, loan_types=LOAN_TYPES)


@loans_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(loan)
    db.session.commit()
    flash('Loan deleted.', 'info')
    return redirect(url_for('loans.list_loans'))


@loans_bp.route('/<int:id>/close', methods=['POST'])
@login_required
def close_loan(id):
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    loan.status = 'closed'
    loan.updated_at = date.today()
    db.session.commit()
    flash('Loan closed.', 'success')
    return redirect(url_for('loans.loan_details', id=loan.id))