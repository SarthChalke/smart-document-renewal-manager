import unittest
from datetime import date, timedelta
from app import app
from models import db, User, Document, DocumentRenewal
from config import TestConfig


class DocumentsTestCase(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test user
        self.user = User(username='docuser', email='docuser@example.com', full_name='Doc Tester')
        self.user.set_password('pass123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_document_expiry_status_computation(self):
        today = date.today()

        # 1. Valid document (expires in 90 days)
        doc_valid = Document(
            user_id=self.user.id,
            title='Passport',
            category='passport',
            expiry_date=today + timedelta(days=90),
            filename='dummy.pdf'
        )
        self.assertEqual(doc_valid.expiry_status, 'valid')
        self.assertEqual(doc_valid.status_display, 'Valid')

        # 2. Expiring soon document (expires in 10 days)
        doc_soon = Document(
            user_id=self.user.id,
            title='Car Insurance',
            category='vehicle_insurance',
            expiry_date=today + timedelta(days=10),
            filename='dummy.pdf'
        )
        self.assertEqual(doc_soon.expiry_status, 'expiring_soon')
        self.assertEqual(doc_soon.status_display, 'Expiring Soon')

        # 3. Expiring today document
        doc_today = Document(
            user_id=self.user.id,
            title='PUC',
            category='vehicle_puc',
            expiry_date=today,
            filename='dummy.pdf'
        )
        self.assertEqual(doc_today.expiry_status, 'expiring_today')
        self.assertEqual(doc_today.status_display, 'Expiring Today')

        # 4. Expired document
        doc_expired = Document(
            user_id=self.user.id,
            title='Old DL',
            category='driving_licence',
            expiry_date=today - timedelta(days=5),
            filename='dummy.pdf'
        )
        self.assertEqual(doc_expired.expiry_status, 'expired')
        self.assertEqual(doc_expired.status_display, 'Expired')

        # 5. Renewed document
        doc_renewed = Document(
            user_id=self.user.id,
            title='Renewed Policy',
            category='health_insurance',
            expiry_date=today + timedelta(days=365),
            renewal_status='Completed',
            filename='dummy.pdf'
        )
        self.assertEqual(doc_renewed.expiry_status, 'renewed')
        self.assertEqual(doc_renewed.status_display, 'Renewed')

        # 6. No expiry date document (e.g. Aadhaar / Birth certificate)
        doc_lifetime = Document(
            user_id=self.user.id,
            title='Aadhaar Card',
            category='aadhaar',
            expiry_date=None,
            filename='dummy.pdf'
        )
        self.assertEqual(doc_lifetime.expiry_status, 'no_expiry')
        self.assertEqual(doc_lifetime.status_display, 'No Expiry Date')

    def test_renewal_workflow(self):
        today = date.today()
        doc = Document(
            user_id=self.user.id,
            title='Bike Insurance',
            category='vehicle_insurance',
            expiry_date=today + timedelta(days=5),
            filename='bike.png'
        )
        db.session.add(doc)
        db.session.commit()

        # Add renewal record
        renewal = DocumentRenewal(
            document_id=doc.id,
            user_id=self.user.id,
            application_date=today,
            status='In Progress',
            previous_expiry_date=doc.expiry_date,
            notes='Applied online'
        )
        db.session.add(renewal)
        doc.renewal_status = 'In Progress'
        db.session.commit()

        self.assertEqual(doc.renewal_status, 'In Progress')
        self.assertEqual(doc.renewals.count(), 1)

        # Complete renewal with new expiry date
        new_exp = today + timedelta(days=365)
        renewal.status = 'Completed'
        renewal.new_expiry_date = new_exp
        doc.renewal_status = 'Completed'
        doc.expiry_date = new_exp
        db.session.commit()

        self.assertEqual(doc.expiry_date, new_exp)
        self.assertEqual(doc.expiry_status, 'renewed')


if __name__ == '__main__':
    unittest.main()

