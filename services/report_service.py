import io
import csv
from datetime import datetime, date
from decimal import Decimal
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether, HRFlowable)


def generate_payment_receipt_pdf(receipt):
    """Generate a clean, professional PDF receipt with the mandatory disclaimer."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    # Title Style
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1b5e20'),
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        'ReceiptSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        alignment=1
    )

    meta_style = ParagraphStyle(
        'ReceiptMeta',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#333333')
    )

    disclaimer_style = ParagraphStyle(
        'ReceiptDisclaimer',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#b71c1c'),
        alignment=1
    )

    # Header
    story.append(Paragraph("Smart Document & Financial Manager", title_style))
    story.append(Paragraph("Personal Loan & EMI Payment Record", subtitle_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2e7d32'), spaceAfter=15))

    # Receipt Info Table
    info_data = [
        [Paragraph(f"<b>Receipt No:</b> {receipt.receipt_number}", meta_style),
         Paragraph(f"<b>Generated On:</b> {receipt.generated_at.strftime('%d-%b-%Y %I:%M %p')}", meta_style)],
        [Paragraph(f"<b>Payment Date:</b> {receipt.payment_date.strftime('%d-%b-%Y')}", meta_style),
         Paragraph(f"<b>Payment Status:</b> <font color='{'green' if receipt.payment_status == 'completed' else 'red'}'><b>{receipt.payment_status.upper()}</b></font>", meta_style)],
    ]
    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Details Table
    details_data = [
        [Paragraph("<b>Transaction Item</b>", meta_style), Paragraph("<b>Details</b>", meta_style)],
        [Paragraph("Loan Name", meta_style), Paragraph(receipt.loan_name, meta_style)],
        [Paragraph("Bank / Lender", meta_style), Paragraph(receipt.lender_name, meta_style)],
        [Paragraph("Installment Reference", meta_style),
         Paragraph(f"EMI #{receipt.emi_number}" if receipt.emi_number else "Direct Loan Payment", meta_style)],
        [Paragraph("Payment Method", meta_style), Paragraph(receipt.payment_method, meta_style)],
        [Paragraph("Transaction Reference", meta_style), Paragraph(receipt.transaction_reference or "N/A", meta_style)],
        [Paragraph("<b>Total Amount Paid</b>", ParagraphStyle('Bld', parent=meta_style, fontSize=11, textColor=colors.HexColor('#1b5e20'))),
         Paragraph(f"<b>₹ {receipt.amount:,.2f}</b>", ParagraphStyle('BldAmt', parent=meta_style, fontSize=12, textColor=colors.HexColor('#1b5e20')))],
    ]

    details_table = Table(details_data, colWidths=[200, 320])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1b5e20')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c8e6c9')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f8e9')),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 30))

    # Mandatory Disclaimer Box
    disclaimer_text = (
        "<b>APPLICATION-GENERATED PAYMENT RECORD — NOT A BANK-ISSUED RECEIPT</b><br/>"
        "This payment record was generated automatically by Smart Document & Financial Management System "
        "based on user input. It is strictly intended for personal record-keeping, audit logs, and tracking purposes. "
        "It does not represent verified bank proof or financial clearance from any banking institution."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[520])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffebee')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ef5350')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_loans_summary_pdf(loans, user_name):
    """Generate a comprehensive PDF report of all user loans."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('RepTitle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#1b5e20'), alignment=1)
    sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#666666'), alignment=1)
    cell_style = ParagraphStyle('RepCell', parent=styles['Normal'], fontSize=8, leading=10)
    head_style = ParagraphStyle('RepHead', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white)

    story.append(Paragraph("Smart Document & Financial Management System", title_style))
    story.append(Paragraph(f"Loans Summary Report — User: {user_name} | Date: {date.today().strftime('%d-%b-%Y')}", sub_style))
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("<b>Loan ID</b>", head_style),
        Paragraph("<b>Loan Name</b>", head_style),
        Paragraph("<b>Lender</b>", head_style),
        Paragraph("<b>Principal (₹)</b>", head_style),
        Paragraph("<b>Interest</b>", head_style),
        Paragraph("<b>Monthly EMI (₹)</b>", head_style),
        Paragraph("<b>Paid (₹)</b>", head_style),
        Paragraph("<b>Outstanding (₹)</b>", head_style),
        Paragraph("<b>Status</b>", head_style)
    ]]

    tot_principal = Decimal('0.00')
    tot_paid = Decimal('0.00')
    tot_outstanding = Decimal('0.00')

    for l in loans:
        p = Decimal(str(l.principal_amount))
        pd = l.total_eligible_paid
        out = l.estimated_outstanding_principal
        tot_principal += p
        tot_paid += pd
        tot_outstanding += out

        table_data.append([
            Paragraph(l.loan_id_code, cell_style),
            Paragraph(l.loan_name, cell_style),
            Paragraph(l.lender_name, cell_style),
            Paragraph(f"{p:,.2f}", cell_style),
            Paragraph(f"{l.annual_interest_rate}%", cell_style),
            Paragraph(f"{l.monthly_emi:,.2f}", cell_style),
            Paragraph(f"{pd:,.2f}", cell_style),
            Paragraph(f"{out:,.2f}", cell_style),
            Paragraph(l.status.upper(), cell_style),
        ])

    table_data.append([
        Paragraph("<b>TOTALS</b>", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph(f"<b>₹ {tot_principal:,.2f}</b>", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph(f"<b>₹ {tot_paid:,.2f}</b>", cell_style),
        Paragraph(f"<b>₹ {tot_outstanding:,.2f}</b>", cell_style),
        Paragraph("", cell_style),
    ])

    col_widths = [60, 85, 75, 65, 40, 65, 65, 65, 45]
    tbl = Table(table_data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e7d32')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f8e9')),
    ]))

    story.append(tbl)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_emi_schedule_pdf(loan, installments, user_name):
    """Generate complete EMI installment schedule PDF for a single loan."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('RepTitle', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#1b5e20'), alignment=1)
    sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#666666'), alignment=1)
    cell_style = ParagraphStyle('RepCell', parent=styles['Normal'], fontSize=8, leading=10)
    head_style = ParagraphStyle('RepHead', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white)

    story.append(Paragraph(f"EMI Schedule: {loan.loan_name} ({loan.loan_id_code})", title_style))
    story.append(Paragraph(f"Lender: {loan.lender_name} | Principal: ₹{loan.principal_amount:,.2f} | Rate: {loan.annual_interest_rate}% | Tenure: {loan.tenure_months} Mo", sub_style))
    story.append(Spacer(1, 15))

    table_data = [[
        Paragraph("<b>#</b>", head_style),
        Paragraph("<b>Due Date</b>", head_style),
        Paragraph("<b>EMI Amount (₹)</b>", head_style),
        Paragraph("<b>Principal (₹)</b>", head_style),
        Paragraph("<b>Interest (₹)</b>", head_style),
        Paragraph("<b>Paid (₹)</b>", head_style),
        Paragraph("<b>Remaining (₹)</b>", head_style),
        Paragraph("<b>Status</b>", head_style)
    ]]

    for item in installments:
        table_data.append([
            Paragraph(str(item.installment_number), cell_style),
            Paragraph(item.due_date.strftime('%d-%b-%Y'), cell_style),
            Paragraph(f"{item.scheduled_amount:,.2f}", cell_style),
            Paragraph(f"{item.principal_component:,.2f}", cell_style),
            Paragraph(f"{item.interest_component:,.2f}", cell_style),
            Paragraph(f"{item.amount_paid:,.2f}", cell_style),
            Paragraph(f"{item.remaining_amount:,.2f}", cell_style),
            Paragraph(item.status.upper(), cell_style),
        ])

    col_widths = [30, 75, 75, 75, 70, 70, 70, 70]
    tbl = Table(table_data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b5e20')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    story.append(tbl)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ─── CSV Export Helpers ──────────────────────────────────────

def export_documents_csv(documents):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Category', 'Document Number', 'Issuing Authority', 'Holder Name',
                     'Issue Date', 'Expiry Date', 'Status', 'Renewal Status', 'Uploaded Date'])
    for d in documents:
        writer.writerow([
            d.title,
            d.category_display,
            d.document_number or '',
            d.issuing_authority or '',
            d.holder_name or '',
            d.issue_date.strftime('%Y-%m-%d') if d.issue_date else '',
            d.expiry_date.strftime('%Y-%m-%d') if d.expiry_date else '',
            d.status_display,
            d.renewal_status,
            d.created_at.strftime('%Y-%m-%d')
        ])
    return output.getvalue()


def export_loans_csv(loans):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Loan ID', 'Loan Name', 'Loan Type', 'Lender Name', 'Reference No',
                     'Principal Amount', 'Interest Rate %', 'Tenure Months', 'Monthly EMI',
                     'Total Amount Payable', 'Total Amount Paid', 'Outstanding Principal',
                     'Start Date', 'Next Due Date', 'Status'])
    for l in loans:
        writer.writerow([
            l.loan_id_code,
            l.loan_name,
            l.loan_type_display,
            l.lender_name,
            l.loan_reference_number or '',
            f"{l.principal_amount:.2f}",
            f"{l.annual_interest_rate:.2f}",
            l.tenure_months,
            f"{l.monthly_emi:.2f}",
            f"{l.total_amount_payable:.2f}",
            f"{l.total_eligible_paid:.2f}",
            f"{l.estimated_outstanding_principal:.2f}",
            l.start_date.strftime('%Y-%m-%d') if l.start_date else '',
            l.next_emi_date.strftime('%Y-%m-%d') if l.next_emi_date else '',
            l.status
        ])
    return output.getvalue()


def export_payments_csv(payments):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Payment Ref', 'Loan ID', 'Loan Name', 'Lender', 'EMI #',
                     'Amount (INR)', 'Payment Date', 'Payment Method', 'Transaction Ref', 'Status', 'Notes'])
    for p in payments:
        writer.writerow([
            p.payment_reference,
            p.loan.loan_id_code if p.loan else '',
            p.loan.loan_name if p.loan else '',
            p.loan.lender_name if p.loan else '',
            p.emi_schedule.installment_number if p.emi_schedule else 'N/A',
            f"{p.amount:.2f}",
            p.payment_date.strftime('%Y-%m-%d') if p.payment_date else '',
            p.payment_method,
            p.transaction_reference or '',
            p.payment_status,
            p.notes or ''
        ])
    return output.getvalue()

