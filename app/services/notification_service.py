from datetime import date, datetime, timedelta
from models import db, Document, Loan, EMISchedule, Notification, UserReminderPreference


def check_and_create_notification(user_id, title, message, category,
                                  related_doc_id=None, related_loan_id=None, related_emi_id=None):
    """Create notification only if a duplicate does not already exist for today."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    query = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.category == category,
        Notification.created_at >= today_start
    )

    if related_doc_id:
        query = query.filter_by(related_document_id=related_doc_id)
    if related_loan_id:
        query = query.filter_by(related_loan_id=related_loan_id)
    if related_emi_id:
        query = query.filter_by(related_emi_id=related_emi_id)

    if query.first():
        return None  # Duplicate suppressed

    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        related_document_id=related_doc_id,
        related_loan_id=related_loan_id,
        related_emi_id=related_emi_id
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def process_user_document_reminders(user_id):
    """Scan user documents and emit expiry notifications based on preferences."""
    pref = UserReminderPreference.query.filter_by(user_id=user_id).first()
    if pref and not pref.in_app_enabled:
        return

    doc_days = pref.doc_days_list if pref else [30, 14, 7, 1]
    today = date.today()

    docs = Document.query.filter(
        Document.user_id == user_id,
        Document.expiry_date.isnot(None)
    ).all()

    for doc in docs:
        if doc.renewal_status == 'Completed':
            continue  # Already renewed

        days_left = (doc.expiry_date - today).days

        if days_left < 0:
            check_and_create_notification(
                user_id=user_id,
                title="Document Expired",
                message=f"Your document '{doc.title}' ({doc.category_display}) expired on {doc.expiry_date.strftime('%d %b %Y')}. Please initiate renewal.",
                category='doc_expired',
                related_doc_id=doc.id
            )
        elif days_left == 0:
            check_and_create_notification(
                user_id=user_id,
                title="Document Expiring Today",
                message=f"Your document '{doc.title}' ({doc.category_display}) expires TODAY ({doc.expiry_date.strftime('%d %b %Y')}).",
                category='doc_expiring',
                related_doc_id=doc.id
            )
        elif days_left in doc_days:
            check_and_create_notification(
                user_id=user_id,
                title=f"Document Expiring in {days_left} Days",
                message=f"Your document '{doc.title}' ({doc.category_display}) expires on {doc.expiry_date.strftime('%d %b %Y')} ({days_left} days remaining).",
                category='doc_expiring',
                related_doc_id=doc.id
            )


def process_user_emi_reminders(user_id):
    """Scan user EMIs and emit due / overdue notifications."""
    pref = UserReminderPreference.query.filter_by(user_id=user_id).first()
    if pref and not pref.in_app_enabled:
        return

    emi_days = pref.emi_days_list if pref else [7, 3, 1, 0]
    today = date.today()

    active_loans = Loan.query.filter_by(user_id=user_id, status='active').all()
    for loan in active_loans:
        unpaid_emis = EMISchedule.query.filter(
            EMISchedule.loan_id == loan.id,
            EMISchedule.status.in_(['upcoming', 'due_today', 'overdue', 'partially_paid'])
        ).all()

        for emi in unpaid_emis:
            if emi.remaining_amount <= 0:
                continue

            days_until = (emi.due_date - today).days

            if days_until < 0:
                check_and_create_notification(
                    user_id=user_id,
                    title="EMI Overdue Alert",
                    message=f"EMI #{emi.installment_number} of ₹{emi.remaining_amount:,.2f} for '{loan.loan_name}' ({loan.lender_name}) was due on {emi.due_date.strftime('%d %b %Y')}.",
                    category='emi_overdue',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id
                )
            elif days_until == 0:
                check_and_create_notification(
                    user_id=user_id,
                    title="EMI Due Today",
                    message=f"Reminder: EMI #{emi.installment_number} of ₹{emi.remaining_amount:,.2f} for '{loan.loan_name}' is due TODAY.",
                    category='emi_due',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id
                )
            elif days_until in emi_days:
                check_and_create_notification(
                    user_id=user_id,
                    title=f"EMI Due in {days_until} Day(s)",
                    message=f"Upcoming EMI #{emi.installment_number} of ₹{emi.remaining_amount:,.2f} for '{loan.loan_name}' is due on {emi.due_date.strftime('%d %b %Y')}.",
                    category='emi_due',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id
                )


def trigger_all_reminders_for_user(user_id):
    """Run both document and EMI reminder checks for a user."""
    process_user_document_reminders(user_id)
    process_user_emi_reminders(user_id)

