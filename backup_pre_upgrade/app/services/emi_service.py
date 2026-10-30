"""EMI schedule generation and management service."""
import calendar
from datetime import date, timedelta
from app import db
from app.models import EMIPayment, Loan


def get_next_emi_date(emi_due_day, after_date=None):
    """Calculate the next EMI due date, handling month-end and leap years."""
    if after_date is None:
        after_date = date.today()

    year = after_date.year
    month = after_date.month

    # Get the last day of the current month
    _, last_day = calendar.monthrange(year, month)
    actual_day = min(emi_due_day, last_day)

    candidate = date(year, month, actual_day)

    if candidate <= after_date:
        # Move to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        _, last_day = calendar.monthrange(year, month)
        actual_day = min(emi_due_day, last_day)
        candidate = date(year, month, actual_day)

    return candidate


def get_emi_date_for_month(emi_due_day, year, month):
    """Get the EMI due date for a specific month, handling month-end dates."""
    _, last_day = calendar.monthrange(year, month)
    actual_day = min(emi_due_day, last_day)
    return date(year, month, actual_day)


def generate_emi_schedule(loan, num_months):
    """Generate EMI schedule entries for a loan.

    Returns list of created EMI records and count of skipped duplicates.
    """
    created = []
    skipped = 0
    start_date = loan.next_emi_date or date.today()

    current_year = start_date.year
    current_month = start_date.month

    for i in range(num_months):
        due_date = get_emi_date_for_month(loan.emi_due_day, current_year, current_month)

        # Check if the first generated date should actually be the start_date
        if i == 0 and due_date < start_date:
            # Move to next month
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1
            due_date = get_emi_date_for_month(loan.emi_due_day, current_year, current_month)

        # Check for duplicates
        existing = EMIPayment.query.filter_by(
            loan_id=loan.id,
            due_date=due_date
        ).first()

        if existing:
            skipped += 1
        else:
            # Check against loan end_date
            if loan.end_date and due_date > loan.end_date:
                break

            emi = EMIPayment(
                loan_id=loan.id,
                amount=loan.monthly_emi,
                due_date=due_date,
                status='upcoming'
            )
            db.session.add(emi)
            created.append(emi)

        # Move to next month
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1

    if created:
        db.session.commit()

    return created, skipped


def update_emi_statuses(loan_id=None):
    """Update EMI statuses based on current date.
    Never marks an EMI as paid automatically.
    """
    today = date.today()

    query = EMIPayment.query.filter(EMIPayment.status.in_(['upcoming', 'due_today', 'pending']))
    if loan_id:
        query = query.filter_by(loan_id=loan_id)

    emis = query.all()
    updated = 0

    for emi in emis:
        new_status = None
        if emi.due_date < today and emi.status != 'paid':
            new_status = 'overdue'
        elif emi.due_date == today and emi.status not in ('paid', 'overdue'):
            new_status = 'due_today'

        if new_status and new_status != emi.status:
            emi.status = new_status
            updated += 1

    if updated:
        db.session.commit()

    return updated


def mark_emi_as_paid(emi_id, payment_date, transaction_reference=None, notes=None):
    """Mark an EMI as paid with payment details."""
    emi = EMIPayment.query.get(emi_id)
    if not emi:
        return None, 'EMI record not found.'

    emi.status = 'paid'
    emi.payment_date = payment_date
    emi.transaction_reference = transaction_reference
    emi.notes = notes

    # Update loan's next EMI date
    loan = emi.loan
    next_unpaid = EMIPayment.query.filter(
        EMIPayment.loan_id == loan.id,
        EMIPayment.status != 'paid',
        EMIPayment.due_date > emi.due_date
    ).order_by(EMIPayment.due_date.asc()).first()

    if next_unpaid:
        loan.next_emi_date = next_unpaid.due_date
    else:
        # Generate next date
        loan.next_emi_date = get_next_emi_date(loan.emi_due_day, emi.due_date)

    db.session.commit()
    return emi, None
