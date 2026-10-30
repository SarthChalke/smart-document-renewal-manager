"""Sample demo data seeder for Smart Document & Financial Manager.
Run with: py seed_data.py
Creates demo user credentials:
Username: demo
Password: demo123
"""
from datetime import date, timedelta
from decimal import Decimal
from app import app
from models import db, User, Document, Loan, EMISchedule, UserReminderPreference
from services.emi_service import (generate_loan_emi_schedule, record_emi_payment,
                                  update_all_emi_statuses)
from services.notification_service import trigger_all_reminders_for_user


def seed():
    with app.app_context():
        print("[+] Seeding database with clean demonstration data...")
        db.create_all()

        # Check if demo user already exists
        user = User.query.filter_by(username='demo').first()
        if user:
            print("Demo user 'demo' already exists. Skipping duplicate creation.")
            return

        # 1. Create Demo User
        user = User(
            full_name='Vighnesh Patil',
            username='demo',
            email='demo@student.edu',
            phone='9876543210'
        )
        user.set_password('demo123')
        db.session.add(user)
        db.session.flush()

        # Preferences
        pref = UserReminderPreference(
            user_id=user.id,
            doc_days_before='30,14,7,1',
            emi_days_before='7,3,1,0',
            in_app_enabled=True
        )
        db.session.add(pref)

        today = date.today()

        # 2. Sample Documents
        docs = [
            Document(
                user_id=user.id,
                title='Aadhaar Card',
                category='aadhaar',
                document_number='9876 5432 1098',
                issuing_authority='UIDAI, Govt of India',
                holder_name='Vighnesh Patil',
                issue_date=today - timedelta(days=1200),
                expiry_date=None,  # Lifetime
                notes='Original smart card linked to mobile number',
                filename='demo_aadhaar.png',
                original_filename='aadhaar_card.png',
                file_size=245000,
                mime_type='image/png'
            ),
            Document(
                user_id=user.id,
                title='Permanent Driving Licence',
                category='driving_licence',
                document_number='MH14 20180012345',
                issuing_authority='RTO Pimpri Chinchwad',
                holder_name='Vighnesh Patil',
                issue_date=today - timedelta(days=800),
                expiry_date=today + timedelta(days=3650),  # Valid
                notes='Classes: LMV, MCWG',
                filename='demo_dl.png',
                original_filename='driving_licence.png',
                file_size=312000,
                mime_type='image/png'
            ),
            Document(
                user_id=user.id,
                title='Two-Wheeler Comprehensive Insurance',
                category='vehicle_insurance',
                document_number='POL-BAJAJ-2026-9871',
                issuing_authority='Bajaj Allianz General Insurance',
                holder_name='Vighnesh Patil',
                issue_date=today - timedelta(days=350),
                expiry_date=today + timedelta(days=15),  # Expiring Soon (15 days)
                notes='Includes zero depreciation cover',
                filename='demo_bike_ins.pdf',
                original_filename='insurance_policy.pdf',
                file_size=489000,
                mime_type='application/pdf'
            ),
            Document(
                user_id=user.id,
                title='Vehicle Emission Certificate (PUC)',
                category='vehicle_puc',
                document_number='PUC-MH14-8842',
                issuing_authority='Transport Dept, Maharashtra',
                holder_name='Vighnesh Patil',
                issue_date=today - timedelta(days=180),
                expiry_date=today,  # Expiring Today!
                notes='Tested at authorized petrol pump',
                filename='demo_puc.png',
                original_filename='puc_certificate.png',
                file_size=180000,
                mime_type='image/png'
            ),
            Document(
                user_id=user.id,
                title='Family Health Mediclaim Policy',
                category='health_insurance',
                document_number='STAR-HLTH-449102',
                issuing_authority='Star Health Insurance',
                holder_name='Vighnesh Patil',
                issue_date=today - timedelta(days=375),
                expiry_date=today - timedelta(days=10),  # Expired (10 days ago)
                renewal_status='Applied',
                notes='Grace period renewal application currently in progress',
                filename='demo_health_ins.pdf',
                original_filename='health_insurance.pdf',
                file_size=560000,
                mime_type='application/pdf'
            ),
        ]
        db.session.add_all(docs)
        db.session.commit()

        # 3. Sample Loans
        loan1 = Loan(
            user_id=user.id,
            loan_id_code='LN-202601-0001',
            loan_name='SBI Education & Laptop Loan',
            loan_type='education',
            lender_name='State Bank of India',
            loan_reference_number='SBI-EDU-99042',
            principal_amount=Decimal('120000.00'),
            annual_interest_rate=Decimal('9.25'),
            start_date=date(today.year, 1, 1),
            end_date=date(today.year + 2, 1, 1),
            tenure_months=24,
            monthly_emi=Decimal('5496.00'),
            emi_due_day=5,
            total_amount_payable=Decimal('131904.00'),
            status='active',
            notes='Educational device financing'
        )

        loan2 = Loan(
            user_id=user.id,
            loan_id_code='LN-202602-0002',
            loan_name='HDFC Two-Wheeler Vehicle Loan',
            loan_type='vehicle',
            lender_name='HDFC Bank',
            loan_reference_number='HDFC-TW-77810',
            principal_amount=Decimal('85000.00'),
            annual_interest_rate=Decimal('10.50'),
            start_date=date(today.year, 2, 1),
            end_date=date(today.year + 1, 8, 1),
            tenure_months=18,
            monthly_emi=Decimal('5122.00'),
            emi_due_day=10,
            total_amount_payable=Decimal('92196.00'),
            status='active',
            notes='Bike loan'
        )

        db.session.add_all([loan1, loan2])
        db.session.commit()

        # 4. Generate EMI Schedules
        generate_loan_emi_schedule(loan1, user.id)
        generate_loan_emi_schedule(loan2, user.id)

        # 5. Record Initial Completed Payments
        # Loan 1: Pay Installment #1
        emi1_l1 = loan1.emi_schedules.filter_by(installment_number=1).first()
        if emi1_l1:
            record_emi_payment(
                emi_id=emi1_l1.id,
                user_id=user.id,
                amount_paying=emi1_l1.scheduled_amount,
                payment_date=emi1_l1.due_date,
                payment_method='UPI',
                transaction_ref='UPI/SBI/20260105001'
            )

        # Loan 2: Pay Installment #1
        emi1_l2 = loan2.emi_schedules.filter_by(installment_number=1).first()
        if emi1_l2:
            record_emi_payment(
                emi_id=emi1_l2.id,
                user_id=user.id,
                amount_paying=emi1_l2.scheduled_amount,
                payment_date=emi1_l2.due_date,
                payment_method='Bank Transfer',
                transaction_ref='NEFT/HDFC/20260210002'
            )

        # Refresh statuses and trigger reminders
        update_all_emi_statuses(user.id)
        trigger_all_reminders_for_user(user.id)

        print("[OK] Demo data seeded successfully!")
        print("---------------------------------------------")
        print("Login Credentials:")
        print("   Username: demo")
        print("   Password: demo123")
        print("---------------------------------------------")


if __name__ == '__main__':
    seed()
