"""Reminder and notification service with APScheduler integration."""
from datetime import date, timedelta, datetime
from app import db
from app.models import (User, Document, Loan, EMIPayment, Notification,
                        UserReminderPreference)

scheduler = None


def init_scheduler(app):
    """Initialize APScheduler for background reminder processing."""
    global scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=lambda: process_all_reminders(app),
            trigger='cron',
            hour=8,
            minute=0,
            id='daily_reminders',
            replace_existing=True
        )
        scheduler.start()
        print("APScheduler started for daily reminders at 08:00")
    except ImportError:
        print("APScheduler not available. Use manual reminder trigger.")
    except Exception as e:
        print(f"Scheduler initialization error: {e}")


def process_all_reminders(app):
    """Process all document and EMI reminders for all users."""
    with app.app_context():
        users = User.query.all()
        for user in users:
            process_document_reminders(user)
            process_emi_reminders(user)
            update_emi_statuses_for_user(user)


def update_emi_statuses_for_user(user):
    """Update EMI statuses (overdue, due_today) for a user's loans."""
    from app.services.emi_service import update_emi_statuses
    loans = Loan.query.filter_by(user_id=user.id).all()
    for loan in loans:
        update_emi_statuses(loan.id)


def process_document_reminders(user):
    """Generate document expiry notifications."""
    prefs = UserReminderPreference.query.filter_by(
        user_id=user.id, reminder_type='document'
    ).first()

    if prefs and not prefs.in_app_enabled:
        return

    reminder_days = prefs.days_list if prefs else [30, 14, 7, 1]
    today = date.today()

    documents = Document.query.filter(
        Document.user_id == user.id,
        Document.expiry_date.isnot(None)
    ).all()

    for doc in documents:
        days_remaining = (doc.expiry_date - today).days

        if days_remaining < 0:
            # Expired
            _create_notification_if_new(
                user_id=user.id,
                title='Document Expired',
                message=f'Your document "{doc.title}" expired on {doc.expiry_date.strftime("%d %b %Y")}.',
                category='doc_expired',
                related_document_id=doc.id,
                dedup_key=f'doc_expired_{doc.id}_{doc.expiry_date}'
            )
        elif days_remaining in reminder_days:
            _create_notification_if_new(
                user_id=user.id,
                title='Document Expiring Soon',
                message=f'Your document "{doc.title}" expires in {days_remaining} day(s) on {doc.expiry_date.strftime("%d %b %Y")}.',
                category='doc_expiring',
                related_document_id=doc.id,
                dedup_key=f'doc_expiring_{doc.id}_{days_remaining}_{doc.expiry_date}'
            )


def process_emi_reminders(user):
    """Generate EMI payment notifications."""
    prefs = UserReminderPreference.query.filter_by(
        user_id=user.id, reminder_type='emi'
    ).first()

    if prefs and not prefs.in_app_enabled:
        return

    reminder_days = prefs.days_list if prefs else [7, 3, 1, 0]
    today = date.today()

    # Get all active loans for user
    loans = Loan.query.filter_by(user_id=user.id, status='active').all()

    for loan in loans:
        # Get unpaid EMIs
        emis = EMIPayment.query.filter(
            EMIPayment.loan_id == loan.id,
            EMIPayment.status != 'paid'
        ).all()

        for emi in emis:
            days_until = (emi.due_date - today).days

            if days_until < 0:
                # Overdue
                _create_notification_if_new(
                    user_id=user.id,
                    title='EMI Overdue',
                    message=f'EMI of ₹{emi.amount:,.2f} for "{loan.loan_name}" was due on {emi.due_date.strftime("%d %b %Y")}. Please make the payment.',
                    category='emi_overdue',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id,
                    dedup_key=f'emi_overdue_{emi.id}_{emi.due_date}'
                )
            elif days_until == 0:
                _create_notification_if_new(
                    user_id=user.id,
                    title='EMI Due Today',
                    message=f'EMI Reminder: Your {loan.loan_type_display} EMI of ₹{emi.amount:,.2f} for "{loan.loan_name}" is due today.',
                    category='emi_due_today',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id,
                    dedup_key=f'emi_due_today_{emi.id}_{emi.due_date}'
                )
            elif days_until in reminder_days:
                _create_notification_if_new(
                    user_id=user.id,
                    title='EMI Due Soon',
                    message=f'EMI Reminder: Your {loan.loan_type_display} EMI of ₹{emi.amount:,.2f} for "{loan.loan_name}" is due on {emi.due_date.strftime("%d %b %Y")}.',
                    category='emi_due_soon',
                    related_loan_id=loan.id,
                    related_emi_id=emi.id,
                    dedup_key=f'emi_due_soon_{emi.id}_{days_until}_{emi.due_date}'
                )


def _create_notification_if_new(user_id, title, message, category,
                                 related_document_id=None, related_loan_id=None,
                                 related_emi_id=None, dedup_key=None):
    """Create a notification only if a similar one doesn't exist today."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Check for duplicate
    query = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.category == category,
        Notification.created_at >= today_start
    )

    if related_document_id:
        query = query.filter_by(related_document_id=related_document_id)
    if related_emi_id:
        query = query.filter_by(related_emi_id=related_emi_id)

    # Additional dedup: check message similarity
    if query.filter(Notification.title == title).first():
        return None

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        related_document_id=related_document_id,
        related_loan_id=related_loan_id,
        related_emi_id=related_emi_id,
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def trigger_reminders_manually(app):
    """Manual trigger for development/testing."""
    process_all_reminders(app)
    return "Reminders processed successfully."
