import unittest
from datetime import date
from decimal import Decimal
from app import app
from models import db, User, Loan, EMISchedule
from config import TestConfig
from services.emi_service import calculate_emi, generate_loan_emi_schedule, update_all_emi_statuses


class EMITestCase(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='emiuser', email='emiuser@example.com', full_name='EMI Tester')
        self.user.set_password('pass123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_emi_calculation_formula(self):
        # 1 Lakh at 12% per annum for 12 months
        # Monthly rate = 1%, N = 12
        # Expected EMI around 8,884.88
        res = calculate_emi(100000, 12.0, 12)
        self.assertAlmostEqual(float(res['monthly_emi']), 8884.88, delta=1.0)
        self.assertGreater(float(res['total_interest']), 6000.0)
        self.assertEqual(float(res['total_payable']), float(res['principal'] + res['total_interest']))

    def test_zero_interest_loan_calculation(self):
        # 60,000 at 0% for 6 months = 10,000 / month, 0 interest
        res = calculate_emi(60000, 0.0, 6)
        self.assertEqual(res['monthly_emi'], Decimal('10000.00'))
        self.assertEqual(res['total_interest'], Decimal('0.00'))
        self.assertEqual(res['total_payable'], Decimal('60000.00'))

    def test_schedule_generation_and_no_duplicates(self):
        loan = Loan(
            user_id=self.user.id,
            loan_id_code='LN-TEST-01',
            loan_name='Test Loan',
            loan_type='personal',
            lender_name='Lender X',
            principal_amount=Decimal('50000.00'),
            annual_interest_rate=Decimal('10.0'),
            start_date=date(2026, 1, 1),
            tenure_months=6,
            monthly_emi=Decimal('8579.00'),
            emi_due_day=5,
            total_amount_payable=Decimal('51474.00'),
            status='active'
        )
        db.session.add(loan)
        db.session.commit()

        # First generation
        created = generate_loan_emi_schedule(loan, self.user.id)
        self.assertEqual(created, 6)
        self.assertEqual(loan.emi_schedules.count(), 6)

        # Second generation attempt must prevent duplicates
        created_again = generate_loan_emi_schedule(loan, self.user.id)
        self.assertEqual(created_again, 0)
        self.assertEqual(loan.emi_schedules.count(), 6)

        # Verify installments have correct sequential numbers and due dates
        first_emi = loan.emi_schedules.filter_by(installment_number=1).first()
        self.assertIsNotNone(first_emi)
        self.assertEqual(first_emi.due_date, date(2026, 1, 5))
        self.assertEqual(first_emi.remaining_amount, first_emi.scheduled_amount)


if __name__ == '__main__':
    unittest.main()

