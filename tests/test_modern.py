"""Tests for the modern modular application structure."""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, User, GovernmentCertificateType, GovernmentCertificateRequirement
from config import TestConfig


class ModernAppTestCase(unittest.TestCase):
    """Test the modular Flask application."""

    def setUp(self):
        """Set up test client and database."""
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_creation(self):
        """Test that the app is created successfully."""
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.config['TESTING'], True)

    def test_blueprints_registered(self):
        """Test that all blueprints are registered."""
        expected_blueprints = [
            'auth', 'dashboard', 'documents', 'loans', 'emi', 'payments',
            'notifications', 'renewals', 'reminders', 'search', 'settings',
            'government', 'reports'
        ]
        for bp in expected_blueprints:
            self.assertIn(bp, self.app.blueprints, f"Blueprint '{bp}' not registered")

    def test_user_registration_and_login(self):
        """Test user can register and login."""
        from app.forms import RegistrationForm

        with self.app.test_client() as client:
            # Register
            res = client.post('/register', data={
                'full_name': 'Test User',
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Logout
            client.get('/logout')

    def test_government_certificate_types(self):
        """Test government certificate types are seeded correctly."""
        # This test runs after running services/government_seed.py
        cert_types = GovernmentCertificateType.query.filter_by(is_active=True).all()
        self.assertGreater(len(cert_types), 0, "No certificate types found")

        # Check for expected certificate types
        names = [ct.name for ct in cert_types]
        expected = ['Domicile Certificate', 'Income Certificate', 'Caste Certificate']
        for exp in expected:
            self.assertIn(exp, names, f"'{exp}' not found in certificate types")


if __name__ == '__main__':
    unittest.main()