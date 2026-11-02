"""Helper utility functions."""
import uuid
import random
import string


def generate_application_number(prefix='APP'):
    """Generate a unique application number with prefix, date and random suffix."""
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'{prefix}-{date_str}-{random_str}'


def generate_receipt_number():
    """Generate a unique receipt number."""
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=5))
    return f'RCT-{date_str}-{random_str}'


def truncate_text(text, max_length=100):
    """Truncate text to max length with ellipsis."""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def format_currency(amount, currency='₹'):
    """Format currency amount with proper formatting."""
    try:
        amount = float(amount)
        return f'{currency}{amount:,.2f}'
    except (ValueError, TypeError):
        return str(amount)


def calculate_days_until_date(target_date):
    """Calculate days between today and target date."""
    from datetime import date
    if not target_date:
        return None
    today = date.today()
    delta = target_date - today
    return delta.days