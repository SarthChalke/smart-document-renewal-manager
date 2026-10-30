import unittest
from datetime import date
from decimal import Decimal
from app import app
from models import db, User, Loan, EMISchedule, LoanPayment, PaymentReceipt
from config import TestConfig
from services.emi_service import (generate_loan_emi_schedule, record_emi_payment,
                                  record_general_loan_payment, cancel_payment_record)
from services.report_service import generate_payment_receipt_pdf, export_payments_csv


class PaymentsTestCase(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='payuser', email='payuser@example.com', full_name='Payment Tester')
        self.user.set_password('pass123')
        db.session.add(self.user)
        db.session.commit()

        # Create loan with 3 installments
        self.loan = Loan(
            user_id=self.user.id,
            loan_id_code='LN-PAY-01',
            loan_name='Test Personal Loan',
            loan_type='personal',
            lender_name='ICICI Bank',
            principal_amount=Decimal('30000.00'),
            annual_interest_rate=Decimal('0.0'),
            start_date=date(2026, 1, 1),
            tenure_months=3,
            monthly_emi=Decimal('10000.00'),
            emi_due_day=5,
            total_amount_payable=Decimal('30000.00'),
            status='active'
        )
        db.session.add(self.loan)
        db.session.commit()
        generate_loan_emi_schedule(self.loan, self.user.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_full_emi_payment_and_receipt(self):
        emi1 = self.loan.emi_schedules.filter_by(installment_number=1).first()
        self.assertIsNotNone(emi1)

        # Record full payment of 10,000
        payment, err = record_emi_payment(
            emi_id=emi1.id,
            user_id=self.user.id,
            amount_paying=Decimal('10000.00'),
            payment_date=date(2026, 1, 5),
            payment_method='UPI',
            transaction_ref='UPI/1234567890'
        )
        self.assertIsNone(err)
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_status, 'completed')

        # Check EMI status updated to paid
        self.assertEqual(emi1.status, 'paid')
        self.assertEqual(emi1.remaining_amount, Decimal('0.00'))
        self.assertEqual(emi1.amount_paid, Decimal('10000.00'))

        # Check Loan updated
        self.assertEqual(self.loan.total_eligible_paid, Decimal('10000.00'))
        self.assertEqual(self.loan.estimated_outstanding_principal, Decimal('20000.00'))

        # Check receipt
        receipt = payment.receipt
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt.receipt_number.startswith('RCT-'))
        self.assertEqual(receipt.amount, Decimal('10000.00'))

        # Verify PDF generation with disclaimer
        pdf_bytes = generate_payment_receipt_pdf(receipt)
        self.assertGreater(len(pdf_bytes), 100)

    def test_partial_emi_payment_and_multiple_partials(self):
        emi2 = self.loan.emi_schedules.filter_by(installment_number=2).first()
        
        # 1. Partial payment 1: 4,000 out of 10,000
        pay1, err1 = record_emi_payment(
            emi_id=emi2.id,
            user_id=self.user.id,
            amount_paying=Decimal('4000.00'),
            payment_date=date(2026, 2, 5),
            payment_method='Cash',
            transaction_ref='CASH-001'
        )
        self.assertIsNone(err1)
        self.assertEqual(emi2.status, 'partially_paid')
        self.assertEqual(emi2.amount_paid, Decimal('4000.00'))
        self.assertEqual(emi2.remaining_amount, Decimal('6000.00'))

        # 2. Overpayment attempt must be rejected
        pay_over, err_over = record_emi_payment(
            emi_id=emi2.id,
            user_id=self.user.id,
            amount_paying=Decimal('7000.00'),  # 7000 > 6000
            payment_date=date(2026, 2, 6),
            payment_method='Cash',
            transaction_ref='CASH-OVER'
        )
        self.assertIsNotNone(err_over)
        self.assertIn('cannot exceed remaining', err_over)

        # 3. Partial payment 2: remaining 6,000
        pay2, err2 = record_emi_payment(
            emi_id=emi2.id,
            user_id=self.user.id,
            amount_paying=Decimal('6000.00'),
            payment_date=date(2026, 2, 7),
            payment_method='Bank Transfer',
            transaction_ref='NEFT-999'
        )
        self.assertIsNone(err2)
        self.assertEqual(emi2.status, 'paid')
        self.assertEqual(emi2.remaining_amount, Decimal('0.00'))
        self.assertEqual(emi2.amount_paid, Decimal('10000.00'))

    def test_payment_cancellation_and_balance_restoration(self):
        emi3 = self.loan.emi_schedules.filter_by(installment_number=3).first()
        payment, _ = record_emi_payment(
            emi_id=emi3.id,
            user_id=self.user.id,
            amount_paying=Decimal('10000.00'),
            payment_date=date(2026, 3, 5),
            payment_method='UPI',
            transaction_ref='UPI-CANCEL-TEST'
        )
        self.assertEqual(emi3.status, 'paid')
        self.assertEqual(self.loan.total_eligible_paid, Decimal('10000.00'))

        # Cancel the payment
        success, cancel_err = cancel_payment_record(
            payment_id=payment.id,
            user_id=self.user.id,
            reason="Incorrect transaction ID entered"
        )
        self.assertTrue(success)
        self.assertEqual(payment.payment_status, 'cancelled')

        # Accounting verification: cancelled payment must NOT count towards eligible paid
        self.assertEqual(self.loan.total_eligible_paid, Decimal('0.00'))
        self.assertEqual(self.loan.estimated_outstanding_principal, Decimal('30000.00'))

        # EMI remaining amount must be restored to full 10,000
        self.assertEqual(emi3.remaining_amount, Decimal('10000.00'))
        self.assertEqual(emi3.amount_paid, Decimal('0.00'))
        self.assertIn(emi3.status, ['upcoming', 'overdue', 'due_today'])

    def test_csv_export_format(self):
        emi1 = self.loan.emi_schedules.filter_by(installment_number=1).first()
        payment, _ = record_emi_payment(
            emi_id=emi1.id,
            user_id=self.user.id,
            amount_paying=Decimal('5000.00'),
            payment_date=date(2026, 1, 5),
            payment_method='UPI',
            transaction_ref='UTR-100'
        )
        csv_data = export_payments_csv([payment])
        self.assertIn('Payment Ref,Loan ID,Loan Name', csv_data)
        self.assertIn('5000.00', csv_data)
        self.assertIn('UTR-100', csv_data)


if __name__ == '__main__':
    unittest.main()

