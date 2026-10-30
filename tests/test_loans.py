import unittest
from datetime import date
from decimal import Decimal
from app import app
from models import db, User, Loan
from config import TestConfig


class LoansTestCase(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(username='loanuser', email='loanuser@example.com', full_name='Loan Tester')
        self.user.set_password('pass123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_loan_and_balances(self):
        loan = Loan(
            user_id=self.user.id,
            loan_id_code='LN-202610-0001',
            loan_name='Car Loan',
            loan_type='vehicle',
            lender_name='HDFC Bank',
            principal_amount=Decimal('400000.00'),
            annual_interest_rate=Decimal('9.50'),
            start_date=date(2026, 1, 1),
            tenure_months=36,
            monthly_emi=Decimal('12815.00'),
            emi_due_day=5,
            total_amount_payable=Decimal('461340.00'),
            status='active'
        )
        db.session.add(loan)
        db.session.commit()

        # Initial state: 0 paid, outstanding = principal
        self.assertEqual(loan.total_eligible_paid, Decimal('0.00'))
        self.assertEqual(loan.estimated_outstanding_principal, Decimal('400000.00'))
        self.assertEqual(loan.repayment_progress_percent, 0.0)
        self.assertEqual(loan.loan_type_display, 'Vehicle Loan')
        self.assertEqual(loan.status_display, 'Active')

    def test_loan_user_data_isolation(self):
        # Create second user
        user2 = User(username='user2', email='user2@example.com', full_name='User Two')
        user2.set_password('pass123')
        db.session.add(user2)
        db.session.commit()

        # Loan for user 1
        l1 = Loan(
            user_id=self.user.id,
            loan_id_code='LN-1',
            loan_name='User1 Loan',
            loan_type='personal',
            lender_name='Bank A',
            principal_amount=10000,
            start_date=date(2026, 1, 1),
            tenure_months=12,
            monthly_emi=900,
            emi_due_day=5,
            total_amount_payable=10800
        )
        # Loan for user 2
        l2 = Loan(
            user_id=user2.id,
            loan_id_code='LN-2',
            loan_name='User2 Private Loan',
            loan_type='home',
            lender_name='Bank B',
            principal_amount=5000000,
            start_date=date(2026, 1, 1),
            tenure_months=240,
            monthly_emi=45000,
            emi_due_day=10,
            total_amount_payable=10800000
        )
        db.session.add_all([l1, l2])
        db.session.commit()

        # Query user 1 loans only
        user1_loans = Loan.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(user1_loans), 1)
        self.assertEqual(user1_loans[0].loan_name, 'User1 Loan')

        # User 2 loans should be isolated
        user2_loans = Loan.query.filter_by(user_id=user2.id).all()
        self.assertEqual(len(user2_loans), 1)
        self.assertEqual(user2_loans[0].loan_name, 'User2 Private Loan')


if __name__ == '__main__':
    unittest.main()

