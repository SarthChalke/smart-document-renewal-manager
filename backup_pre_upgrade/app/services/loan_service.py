"""Loan management service."""
from app.models import Loan, EMIPayment
from app import db


def get_loan_summary(user_id):
    """Get summary statistics for a user's loans."""
    loans = Loan.query.filter_by(user_id=user_id).all()

    total_loans = len(loans)
    active_loans = sum(1 for l in loans if l.status == 'active')
    monthly_emi_total = sum(float(l.monthly_emi) for l in loans if l.status == 'active')

    # Outstanding principal estimate
    outstanding_total = 0
    has_estimate = False
    for l in loans:
        if l.status == 'active' and l.outstanding_estimate is not None:
            outstanding_total += l.outstanding_estimate
            has_estimate = True

    return {
        'total_loans': total_loans,
        'active_loans': active_loans,
        'monthly_emi_total': monthly_emi_total,
        'outstanding_total': outstanding_total if has_estimate else None,
    }


def get_loan_distribution(user_id):
    """Get loan count by type for charts."""
    from sqlalchemy import func
    results = db.session.query(
        Loan.loan_type,
        func.count(Loan.id)
    ).filter_by(user_id=user_id).group_by(Loan.loan_type).all()

    from app.models import LOAN_TYPE_DICT
    return {LOAN_TYPE_DICT.get(lt, lt): count for lt, count in results}
