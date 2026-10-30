"""EMI management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models import Loan, EMIPayment, Notification
from app.forms import EMIGenerateForm, EMIPaymentForm
from app.services.emi_service import generate_emi_schedule, update_emi_statuses, mark_emi_as_paid

emi_bp = Blueprint('emi', __name__, url_prefix='/emi')


@emi_bp.route('/')
@login_required
def list_emi():
    page = request.args.get('page', 1, type=int)
    loan_id = request.args.get('loan_id', '', type=str)
    status = request.args.get('status', '').strip()
    month = request.args.get('month', '', type=str)
    year = request.args.get('year', '', type=str)

    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    user_loan_ids = [l.id for l in user_loans]

    if not user_loan_ids:
        return render_template('emi/list.html',
                               emis=None,
                               loans=user_loans,
                               current_loan_id='',
                               current_status=status,
                               current_month=month,
                               current_year=year)

    # Update statuses
    for lid in user_loan_ids:
        update_emi_statuses(lid)

    query = db.session.query(EMIPayment, Loan).join(
        Loan, EMIPayment.loan_id == Loan.id
    ).filter(EMIPayment.loan_id.in_(user_loan_ids))

    if loan_id:
        query = query.filter(EMIPayment.loan_id == int(loan_id))

    if status:
        query = query.filter(EMIPayment.status == status)

    if month and year:
        query = query.filter(
            db.extract('month', EMIPayment.due_date) == int(month),
            db.extract('year', EMIPayment.due_date) == int(year)
        )
    elif year:
        query = query.filter(db.extract('year', EMIPayment.due_date) == int(year))

    query = query.order_by(EMIPayment.due_date.asc())
    emis = query.paginate(page=page, per_page=15, error_out=False)

    return render_template('emi/list.html',
                           emis=emis,
                           loans=user_loans,
                           current_loan_id=loan_id,
                           current_status=status,
                           current_month=month,
                           current_year=year)


@emi_bp.route('/generate/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def generate_schedule(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    form = EMIGenerateForm()
    if form.validate_on_submit():
        created, skipped = generate_emi_schedule(loan, form.num_months.data)
        if created:
            flash(f'{len(created)} EMI records generated. {skipped} duplicates skipped.', 'success')
        else:
            flash(f'No new records generated. {skipped} duplicates skipped.', 'info')
        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    return render_template('emi/generate.html', form=form, loan=loan)


@emi_bp.route('/<int:emi_id>/pay', methods=['GET', 'POST'])
@login_required
def pay_emi(emi_id):
    emi = EMIPayment.query.get_or_404(emi_id)
    loan = Loan.query.get_or_404(emi.loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    if emi.status == 'paid':
        flash('This EMI is already marked as paid.', 'info')
        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    form = EMIPaymentForm()
    if form.validate_on_submit():
        emi_record, error = mark_emi_as_paid(
            emi.id,
            form.payment_date.data,
            form.transaction_reference.data,
            form.notes.data
        )

        if error:
            flash(error, 'danger')
        else:
            # Create notification
            notification = Notification(
                user_id=current_user.id,
                title='Payment Status Updated',
                message=f'EMI of ₹{emi.amount:,.2f} for "{loan.loan_name}" due on {emi.due_date.strftime("%d %b %Y")} has been marked as paid.',
                category='payment_updated',
                related_loan_id=loan.id,
                related_emi_id=emi.id,
            )
            db.session.add(notification)
            db.session.commit()

            flash('EMI marked as paid.', 'success')

        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    form.payment_date.data = date.today()
    return render_template('emi/pay.html', form=form, emi=emi, loan=loan)


@emi_bp.route('/upcoming')
@login_required
def upcoming():
    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    user_loan_ids = [l.id for l in user_loans]

    emis = []
    if user_loan_ids:
        for lid in user_loan_ids:
            update_emi_statuses(lid)

        emis = db.session.query(EMIPayment, Loan).join(
            Loan, EMIPayment.loan_id == Loan.id
        ).filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status.in_(['upcoming', 'due_today']),
            EMIPayment.due_date >= date.today()
        ).order_by(EMIPayment.due_date.asc()).all()

    return render_template('emi/upcoming.html', emis=emis)


@emi_bp.route('/overdue')
@login_required
def overdue():
    user_loans = Loan.query.filter_by(user_id=current_user.id).all()
    user_loan_ids = [l.id for l in user_loans]

    emis = []
    if user_loan_ids:
        for lid in user_loan_ids:
            update_emi_statuses(lid)

        emis = db.session.query(EMIPayment, Loan).join(
            Loan, EMIPayment.loan_id == Loan.id
        ).filter(
            EMIPayment.loan_id.in_(user_loan_ids),
            EMIPayment.status == 'overdue'
        ).order_by(EMIPayment.due_date.asc()).all()

    return render_template('emi/overdue.html', emis=emis)


@emi_bp.route('/<int:emi_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_emi(emi_id):
    """Allow correction of an EMI payment record."""
    emi = EMIPayment.query.get_or_404(emi_id)
    loan = Loan.query.get_or_404(emi.loan_id)
    if loan.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        new_status = request.form.get('status')
        if new_status == 'unpaid' and emi.status == 'paid':
            # Reverse payment
            emi.status = 'upcoming' if emi.due_date >= date.today() else 'overdue'
            emi.payment_date = None
            emi.transaction_reference = None
            db.session.commit()
            flash('EMI payment reversed.', 'warning')
        elif new_status == 'paid' and emi.status != 'paid':
            return redirect(url_for('emi.pay_emi', emi_id=emi.id))

        return redirect(url_for('loans.view_loan', loan_id=loan.id))

    return render_template('emi/edit.html', emi=emi, loan=loan)
