import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from models import db, Loan, EMISchedule, LoanPayment, PaymentReceipt, AuditLog, Notification


def round_curr(val):
    """Round to 2 decimal places."""
    return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_emi(principal, annual_interest_rate, tenure_months):
    """Standard reducing-balance formula:
    EMI = P * R * (1 + R)^N / ((1 + R)^N - 1)
    Handles zero-interest loan separately.
    Returns Decimal values.
    """
    P = Decimal(str(principal))
    N = int(tenure_months)
    rate = Decimal(str(annual_interest_rate))

    if N <= 0 or P <= 0:
        return {
            'monthly_emi': Decimal('0.00'),
            'total_interest': Decimal('0.00'),
            'total_payable': Decimal('0.00'),
            'principal': P
        }

    if rate <= Decimal('0.00'):
        # Zero-interest loan
        monthly_emi = round_curr(P / Decimal(N))
        total_payable = P
        total_interest = Decimal('0.00')
        return {
            'monthly_emi': monthly_emi,
            'total_interest': total_interest,
            'total_payable': total_payable,
            'principal': P
        }

    # Monthly interest rate
    R = (rate / Decimal('100.0')) / Decimal('12.0')
    
    # (1 + R)^N
    pow_factor = (Decimal('1.0') + R) ** N
    
    # EMI = P * R * pow_factor / (pow_factor - 1)
    numerator = P * R * pow_factor
    denominator = pow_factor - Decimal('1.0')
    
    emi = round_curr(numerator / denominator)
    total_payable = round_curr(emi * Decimal(N))
    total_interest = round_curr(total_payable - P)

    return {
        'monthly_emi': emi,
        'total_interest': total_interest,
        'total_payable': total_payable,
        'principal': P
    }


def get_due_date_for_month(year, month, due_day):
    """Get exact due date handling varying month lengths (e.g. Feb 28/29, 30 days)."""
    _, last_day = calendar.monthrange(year, month)
    day = min(int(due_day), last_day)
    return date(year, month, day)


def generate_loan_emi_schedule(loan, user_id):
    """Generate or refresh complete EMI schedule installments for a Loan."""
    tenure = int(loan.tenure_months)
    principal = Decimal(str(loan.principal_amount))
    rate = Decimal(str(loan.annual_interest_rate or 0))
    monthly_emi = Decimal(str(loan.monthly_emi))
    due_day = int(loan.emi_due_day)
    start_date = loan.start_date

    # Monthly interest rate decimal
    R = (rate / Decimal('100.0')) / Decimal('12.0') if rate > 0 else Decimal('0.0')

    current_balance = principal
    created_count = 0

    curr_year = start_date.year
    curr_month = start_date.month

    for inst_num in range(1, tenure + 1):
        due_d = get_due_date_for_month(curr_year, curr_month, due_day)
        
        # Check if installment already exists
        existing = EMISchedule.query.filter_by(
            loan_id=loan.id,
            installment_number=inst_num
        ).first()

        if not existing:
            # Calculate interest & principal components
            if rate > 0:
                interest_comp = round_curr(current_balance * R)
                principal_comp = round_curr(monthly_emi - interest_comp)
                if inst_num == tenure:
                    # Final adjustment for rounding
                    principal_comp = current_balance
                    scheduled_amt = principal_comp + interest_comp
                else:
                    scheduled_amt = monthly_emi
                current_balance = max(Decimal('0.00'), current_balance - principal_comp)
            else:
                interest_comp = Decimal('0.00')
                principal_comp = monthly_emi
                scheduled_amt = monthly_emi
                current_balance = max(Decimal('0.00'), current_balance - principal_comp)

            # Determine initial status
            today = date.today()
            if due_d < today:
                status = 'overdue'
            elif due_d == today:
                status = 'due_today'
            else:
                status = 'upcoming'

            installment = EMISchedule(
                loan_id=loan.id,
                user_id=user_id,
                installment_number=inst_num,
                scheduled_amount=scheduled_amt,
                principal_component=principal_comp,
                interest_component=interest_comp,
                due_date=due_d,
                amount_paid=Decimal('0.00'),
                remaining_amount=scheduled_amt,
                status=status
            )
            db.session.add(installment)
            created_count += 1

        # Advance to next month
        if curr_month == 12:
            curr_month = 1
            curr_year += 1
        else:
            curr_month += 1

    db.session.commit()
    return created_count


def update_all_emi_statuses(user_id):
    """Dynamically update overdue / due_today statuses based on current date.
    Never marks an unpaid EMI as paid.
    """
    today = date.today()
    unpaid_emis = EMISchedule.query.filter(
        EMISchedule.user_id == user_id,
        EMISchedule.status.in_(['upcoming', 'due_today', 'overdue', 'partially_paid'])
    ).all()

    updated = False
    for emi in unpaid_emis:
        if emi.remaining_amount <= 0:
            if emi.status != 'paid':
                emi.status = 'paid'
                updated = True
        elif emi.amount_paid > 0:
            if emi.status != 'partially_paid':
                emi.status = 'partially_paid'
                updated = True
        else:
            if emi.due_date < today and emi.status != 'overdue':
                emi.status = 'overdue'
                updated = True
            elif emi.due_date == today and emi.status != 'due_today':
                emi.status = 'due_today'
                updated = True
            elif emi.due_date > today and emi.status != 'upcoming':
                emi.status = 'upcoming'
                updated = True

    if updated:
        db.session.commit()


def record_emi_payment(emi_id, user_id, amount_paying, payment_date, payment_method,
                       transaction_ref, notes=None, receipt_filename=None, ip_address=None):
    """Record an EMI payment (full or partial) with database transaction.
    Generates payment record, updates installment status and loan balances, generates receipt.
    """
    emi = EMISchedule.query.filter_by(id=emi_id, user_id=user_id).first()
    if not emi:
        return None, "EMI schedule installment not found."

    loan = emi.loan
    amount_paying = round_curr(amount_paying)

    if amount_paying <= 0:
        return None, "Payment amount must be greater than zero."

    if amount_paying > emi.remaining_amount:
        return None, f"Payment amount (₹{amount_paying:,.2f}) cannot exceed remaining amount (₹{emi.remaining_amount:,.2f})."

    try:
        # 1. Update EMI Schedule
        new_paid = round_curr(emi.amount_paid + amount_paying)
        new_remaining = round_curr(emi.remaining_amount - amount_paying)
        
        emi.amount_paid = new_paid
        emi.remaining_amount = new_remaining
        emi.payment_date = payment_date

        is_full = (new_remaining <= Decimal('0.00'))
        if is_full:
            emi.status = 'paid'
        else:
            emi.status = 'partially_paid'

        # 2. Generate unique payment reference
        count_payments = LoanPayment.query.count() + 1
        date_str = payment_date.strftime('%Y%m')
        pay_ref = f"PAY-{date_str}-{count_payments:05d}"

        # 3. Create LoanPayment record
        payment = LoanPayment(
            user_id=user_id,
            loan_id=loan.id,
            emi_id=emi.id,
            payment_reference=pay_ref,
            amount=amount_paying,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed',
            receipt_filename=receipt_filename,
            notes=notes,
            is_partial=not is_full
        )
        db.session.add(payment)
        db.session.flush()  # get payment.id

        # 4. Create PaymentReceipt record
        count_receipts = PaymentReceipt.query.count() + 1
        rcpt_ref = f"RCT-{date_str}-{count_receipts:05d}"
        receipt = PaymentReceipt(
            receipt_number=rcpt_ref,
            payment_id=payment.id,
            user_id=user_id,
            loan_name=loan.loan_name,
            lender_name=loan.lender_name,
            emi_number=emi.installment_number,
            amount=amount_paying,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed'
        )
        db.session.add(receipt)

        # 5. Update next EMI due date on Loan
        next_unpaid = EMISchedule.query.filter(
            EMISchedule.loan_id == loan.id,
            EMISchedule.status != 'paid',
            EMISchedule.id != emi.id
        ).order_by(EMISchedule.due_date.asc()).first()

        if next_unpaid:
            loan.next_emi_date = next_unpaid.due_date
        elif is_full:
            # Check if all EMIs for loan are paid
            remaining_unpaid = EMISchedule.query.filter(
                EMISchedule.loan_id == loan.id,
                EMISchedule.status != 'paid'
            ).count()
            if remaining_unpaid == 0:
                loan.status = 'completed'
                loan.next_emi_date = None

        # 6. Audit Log
        audit = AuditLog(
            user_id=user_id,
            action='PAYMENT_RECORDED',
            entity_type='LoanPayment',
            entity_id=payment.id,
            details=f"Recorded payment of ₹{amount_paying:,.2f} for Loan '{loan.loan_name}' (EMI #{emi.installment_number}). Status: {'Paid' if is_full else 'Partially Paid'}.",
            ip_address=ip_address
        )
        db.session.add(audit)

        # 7. Notification
        notif = Notification(
            user_id=user_id,
            title="Payment Successfully Recorded",
            message=f"Payment of ₹{amount_paying:,.2f} for '{loan.loan_name}' (Installment #{emi.installment_number}) recorded. Receipt: {rcpt_ref}",
            category='payment_recorded',
            related_loan_id=loan.id,
            related_emi_id=emi.id
        )
        db.session.add(notif)

        db.session.commit()
        return payment, None

    except Exception as e:
        db.session.rollback()
        return None, f"Database transaction failed: {str(e)}"


def record_general_loan_payment(loan_id, user_id, amount, payment_date, payment_method,
                                transaction_ref, notes=None, receipt_filename=None, ip_address=None):
    """Record a direct lump-sum or extra loan payment."""
    loan = Loan.query.filter_by(id=loan_id, user_id=user_id).first()
    if not loan:
        return None, "Loan not found."

    amount = round_curr(amount)
    if amount <= 0:
        return None, "Payment amount must be greater than zero."

    try:
        count_payments = LoanPayment.query.count() + 1
        date_str = payment_date.strftime('%Y%m')
        pay_ref = f"PAY-{date_str}-{count_payments:05d}"

        payment = LoanPayment(
            user_id=user_id,
            loan_id=loan.id,
            emi_id=None,
            payment_reference=pay_ref,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed',
            receipt_filename=receipt_filename,
            notes=notes,
            is_partial=False
        )
        db.session.add(payment)
        db.session.flush()

        count_receipts = PaymentReceipt.query.count() + 1
        rcpt_ref = f"RCT-{date_str}-{count_receipts:05d}"
        receipt = PaymentReceipt(
            receipt_number=rcpt_ref,
            payment_id=payment.id,
            user_id=user_id,
            loan_name=loan.loan_name,
            lender_name=loan.lender_name,
            emi_number=None,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            payment_status='completed'
        )
        db.session.add(receipt)

        audit = AuditLog(
            user_id=user_id,
            action='DIRECT_LOAN_PAYMENT',
            entity_type='LoanPayment',
            entity_id=payment.id,
            details=f"Recorded direct payment of ₹{amount:,.2f} for Loan '{loan.loan_name}'.",
            ip_address=ip_address
        )
        db.session.add(audit)

        db.session.commit()
        return payment, None
    except Exception as e:
        db.session.rollback()
        return None, f"Database transaction failed: {str(e)}"


def cancel_payment_record(payment_id, user_id, reason="User cancelled", ip_address=None):
    """Cancel a completed payment and reverse its accounting impact."""
    payment = LoanPayment.query.filter_by(id=payment_id, user_id=user_id).first()
    if not payment:
        return False, "Payment record not found."

    if payment.payment_status == 'cancelled':
        return False, "This payment is already cancelled."

    try:
        # If attached to an EMI schedule, reverse remaining amount
        if payment.emi_id:
            emi = db.session.get(EMISchedule, payment.emi_id)
            if emi:
                emi.amount_paid = max(Decimal('0.00'), round_curr(emi.amount_paid - payment.amount))
                emi.remaining_amount = round_curr(emi.scheduled_amount - emi.amount_paid)
                if emi.amount_paid == 0:
                    today = date.today()
                    emi.status = 'overdue' if emi.due_date < today else ('due_today' if emi.due_date == today else 'upcoming')
                    emi.payment_date = None
                else:
                    emi.status = 'partially_paid'

        payment.payment_status = 'cancelled'
        payment.notes = (payment.notes or "") + f" [Cancelled: {reason}]"

        if payment.receipt:
            payment.receipt.payment_status = 'cancelled'

        audit = AuditLog(
            user_id=user_id,
            action='PAYMENT_CANCELLED',
            entity_type='LoanPayment',
            entity_id=payment.id,
            details=f"Payment {payment.payment_reference} (₹{payment.amount:,.2f}) cancelled. Reason: {reason}",
            ip_address=ip_address
        )
        db.session.add(audit)

        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, f"Cancellation failed: {str(e)}"
