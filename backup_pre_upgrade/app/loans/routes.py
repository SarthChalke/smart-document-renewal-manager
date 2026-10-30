"""Loan management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Loan, EMIPayment, LOAN_TYPES, LOAN_STATUSES
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
            (Loan.loan_name.ilike(f'%{search}%')) |
            (Loan.lender_name.ilike(f'%{search}%'))
        )

    if loan_type:
        query = query.filter_by(loan_type=loan_type)

    if status:
        query = query.filter_by(status=status)

    query = query.order_by(Loan.created_at.desc())
    loans = query.paginate(page=page, per_page=10, error_out=False)

    return render_template('loans/list.html',
                           loans=loans,
                           loan_types=LOAN_TYPES,
                           loan_statuses=LOAN_STATUSES,
                           search=search,
                           current_type=loan_type,
                           current_status=status)


@loans_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_loan():
    form = LoanForm()
    if form.validate_on_submit():
        loan = Loan(
            user_id=current_user.id,
            loan_name=form.loan_name.data,
            lender_name=form.lender_name.data,
            loan_type=form.loan_type.data,
            principal_amount=form.principal_amount.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            monthly_emi=form.monthly_emi.data,
            emi_due_day=form.emi_due_day.data,
            next_emi_date=form.next_emi_date.data,
            status=form.status.data,
            notes=form.notes.data,
        )
        db.session.add(loan)
        db.session.commit()

        flash('Loan added successfully!', 'success')
        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    return render_template('loans/add.html', form=form)


@loans_bp.route('/<int:loan_id>')
@login_required
def view_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    # Get EMI payments
    emis = EMIPayment.query.filter_by(loan_id=loan.id).order_by(EMIPayment.due_date.asc()).all()

    # Update statuses
    from app.services.emi_service import update_emi_statuses
    update_emi_statuses(loan.id)

    upcoming = [e for e in emis if e.computed_status in ('upcoming', 'due_today')]
    paid = [e for e in emis if e.status == 'paid']
    overdue = [e for e in emis if e.computed_status == 'overdue']

    return render_template('loans/view.html',
                           loan=loan,
                           emis=emis,
                           upcoming=upcoming,
                           paid=paid,
                           overdue=overdue)


@loans_bp.route('/<int:loan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    form = LoanForm(obj=loan)
    if form.validate_on_submit():
        loan.loan_name = form.loan_name.data
        loan.lender_name = form.lender_name.data
        loan.loan_type = form.loan_type.data
        loan.principal_amount = form.principal_amount.data
        loan.interest_rate = form.interest_rate.data
        loan.start_date = form.start_date.data
        loan.end_date = form.end_date.data
        loan.monthly_emi = form.monthly_emi.data
        loan.emi_due_day = form.emi_due_day.data
        loan.next_emi_date = form.next_emi_date.data
        loan.status = form.status.data
        loan.notes = form.notes.data
        db.session.commit()

        flash('Loan updated.', 'success')
        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    return render_template('loans/edit.html', form=form, loan=loan)


@loans_bp.route('/<int:loan_id>/delete', methods=['POST'])
@login_required
def delete_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    db.session.delete(loan)
    db.session.commit()
    flash('Loan and all associated EMI records deleted.', 'success')
    return redirect(url_for('loans.list_loans'))
