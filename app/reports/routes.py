"""Reports routes."""
from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import extract
from app import db
from app.models import Document, Loan, LoanPayment, PaymentReceipt
from app.services.report_service import (
    generate_payment_receipt_pdf,
    generate_loans_summary_pdf,
    generate_emi_schedule_pdf,
    export_documents_csv,
    export_loans_csv,
    export_payments_csv
)

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard."""
    return render_template('reports/index.html')


@reports_bp.route('/loans/pdf')
@login_required
def loans_pdf():
    """Generate loans summary PDF."""
    return generate_loans_summary_pdf(current_user.id)


@reports_bp.route('/loans/<int:id>/schedule/pdf')
@login_required
def loan_schedule_pdf(id):
    """Generate loan EMI schedule PDF."""
    loan = Loan.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return generate_emi_schedule_pdf(loan.id)


@reports_bp.route('/documents/csv')
@login_required
def documents_csv():
    """Export documents as CSV."""
    return export_documents_csv(current_user.id)


@reports_bp.route('/loans/csv')
@login_required
def loans_csv():
    """Export loans as CSV."""
    return export_loans_csv(current_user.id)


@reports_bp.route('/payments/csv')
@login_required
def payments_csv():
    """Export payments as CSV."""
    return export_payments_csv(current_user.id)


@reports_bp.route('/payment-receipt/<int:id>')
@login_required
def payment_receipt_pdf(id):
    """Download payment receipt PDF."""
    receipt = PaymentReceipt.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return send_file(
        receipt.pdf_filename,
        as_attachment=True,
        download_name=f'receipt_{receipt.receipt_number}.pdf'
    )