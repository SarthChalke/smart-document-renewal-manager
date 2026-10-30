import unittest
from app import app
from models import db, User
from config import TestConfig


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_registration_and_login(self):
        # Register user
        res = self.app.post('/register', data={
            'full_name': 'Test Student',
            'username': 'teststudent',
            'email': 'student@example.com',
            'phone': '9876543210',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

        # Verify user in database
        user = User.query.filter_by(username='teststudent').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('password123'))
        self.assertFalse(user.check_password('wrongpassword'))

        # Login with correct password
        login_res = self.app.post('/login', data={
            'username': 'teststudent',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back', login_res.data)

        # Logout
        logout_res = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'You have been securely logged out', logout_res.data)

    def test_duplicate_registration_prevented(self):
        # Create first user
        user = User(username='existinguser', email='exist@example.com', full_name='Existing')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        # Try duplicate username
        res = self.app.post('/register', data={
            'full_name': 'Duplicate User',
            'username': 'existinguser',
            'email': 'different@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Username is already taken', res.data)

        # Try duplicate email
        res2 = self.app.post('/register', data={
            'full_name': 'Duplicate User',
            'username': 'newunique',
            'email': 'exist@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Email is already registered', res2.data)

    def test_protected_routes_require_login(self):
        res = self.app.get('/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])


if __name__ == '__main__':
    unittest.main()

