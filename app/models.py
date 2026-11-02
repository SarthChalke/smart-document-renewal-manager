from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─── Categories & Type Definitions ──────────────────────────

DOCUMENT_CATEGORIES = [
    ('aadhaar', 'Aadhaar Card'),
    ('pan', 'PAN Card'),
    ('driving_licence', 'Driving Licence'),
    ('passport', 'Passport'),
    ('vehicle_insurance', 'Vehicle Insurance'),
    ('health_insurance', 'Health Insurance'),
    ('life_insurance', 'Life Insurance'),
    ('vehicle_puc', 'Vehicle PUC Certificate'),
    ('vehicle_rc', 'Vehicle Registration Certificate (RC)'),
    ('property', 'Property Documents'),
    ('education', 'Educational Certificates'),
    ('business_licence', 'Business Licences'),
    ('other', 'Other Documents'),
]
DOCUMENT_CATEGORY_DICT = dict(DOCUMENT_CATEGORIES)

LOAN_TYPES = [
    ('personal', 'Personal Loan'),
    ('home', 'Home Loan'),
    ('education', 'Education Loan'),
    ('vehicle', 'Vehicle Loan'),
    ('business', 'Business Loan'),
    ('other', 'Other Loan'),
]
LOAN_TYPE_DICT = dict(LOAN_TYPES)

LOAN_STATUSES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('overdue', 'Overdue'),
    ('closed', 'Closed'),
]
LOAN_STATUS_DICT = dict(LOAN_STATUSES)

PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('Bank Transfer', 'Bank Transfer'),
    ('UPI', 'UPI'),
    ('Debit Card', 'Debit Card'),
    ('Credit Card', 'Credit Card'),
    ('Other', 'Other'),
]

PAYMENT_STATUSES = [
    ('completed', 'Completed'),
    ('pending', 'Pending'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]

RENEWAL_STATUSES = [
    ('Not Started', 'Not Started'),
    ('Applied', 'Applied'),
    ('In Progress', 'In Progress'),
    ('Completed', 'Completed'),
    ('Rejected', 'Rejected'),
]

# ─── User Model ──────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (User-specific data isolation)
    documents = db.relationship('Document', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    renewals = db.relationship('DocumentRenewal', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    loans = db.relationship('Loan', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    emi_schedules = db.relationship('EMISchedule', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    loan_payments = db.relationship('LoanPayment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    receipts = db.relationship('PaymentReceipt', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reminder_preference = db.relationship('UserReminderPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    government_applications = db.relationship(
        'GovernmentApplication',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ─── Document Model ──────────────────────────────────────────

class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    document_number = db.Column(db.String(100), nullable=True, index=True)
    issuing_authority = db.Column(db.String(150), nullable=True)
    holder_name = db.Column(db.String(150), nullable=True)
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True, index=True)

    notes = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)

    # Dynamic fields for expiry status logic
    expiry_status = db.Column(db.String(50), nullable=True, index=True)
    renewal_status = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    renewals = db.relationship('DocumentRenewal', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='document', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def category_display(self):
        return DOCUMENT_CATEGORY_DICT.get(self.category, self.category.title())

    @property
    def expiry_status_display(self):
        status_map = {
            'valid': 'Valid',
            'expiring_soon': 'Expiring Soon',
            'expiring_today': 'Expiring Today',
            'expired': 'Expired',
            'renewed': 'Renewed',
            'no_expiry': 'No Expiry'
        }
        return status_map.get(self.expiry_status, self.expiry_status or 'Unknown')

    def __repr__(self):
        return f'<Document {self.title}>'


# ─── Document Renewal Model ───────────────────────────────────

class DocumentRenewal(db.Model):
    __tablename__ = 'document_renewals'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    application_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_completion_date = db.Column(db.Date, nullable=True)
    actual_renewal_date = db.Column(db.Date, nullable=True)
    previous_expiry_date = db.Column(db.Date, nullable=True)
    new_expiry_date = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(50), nullable=False, default='Not Started')
    notes = db.Column(db.Text, nullable=True)

    # File upload support
    renewal_document_filename = db.Column(db.String(255), nullable=True)
    renewal_document_original_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<DocumentRenewal {self.id} for Doc {self.document_id}>'


# ─── Loan Model ───────────────────────────────────────────────

class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    loan_type = db.Column(db.String(50), nullable=False, index=True)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=True)
    loan_tenure_months = db.Column(db.Integer, nullable=False)
    monthly_emi = db.Column(db.Numeric(10, 2), nullable=True)

    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(50), nullable=False, default='active', index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Calculated fields
    total_amount_payable = db.Column(db.Numeric(15, 2), nullable=True)
    total_eligible_paid = db.Column(db.Numeric(15, 2), default=0)
    estimated_outstanding_principal = db.Column(db.Numeric(15, 2), nullable=True)

    # Relationships
    emi_schedule = db.relationship('EMISchedule', backref='loan', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('LoanPayment', backref='loan', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='loan', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def loan_type_display(self):
        return LOAN_TYPE_DICT.get(self.loan_type, self.loan_type.title())

    @property
    def status_display(self):
        return LOAN_STATUSES_DICT.get(self.status, self.status.title())

    def __repr__(self):
        return f'<Loan {self.id} {self.loan_type_display}>'


# ─── EMI Schedule Model ───────────────────────────────────────

class EMISchedule(db.Model):
    __tablename__ = 'emi_schedule'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    emi_number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    principal_component = db.Column(db.Numeric(10, 2), nullable=False)
    interest_component = db.Column(db.Numeric(10, 2), nullable=False)
    total_component = db.Column(db.Numeric(10, 2), nullable=False)

    paid_amount = db.Column(db.Numeric(10, 2), nullable=True)
    payment_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='unpaid', index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<EMISchedule {self.id} EMI {self.emi_number}>'


# ─── Loan Payment Model ───────────────────────────────────────

class LoanPayment(db.Model):
    __tablename__ = 'loan_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)

    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')

    receipt_number = db.Column(db.String(100), nullable=True, unique=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    receipt = db.relationship('PaymentReceipt', backref='loan_payment', uselist=False, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='loan_payment', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def payment_method_display(self):
        return PAYMENT_METHODS_DICT.get(self.payment_method, self.payment_method)

    @property
    def payment_status_display(self):
        return PAYMENT_STATUSES_DICT.get(self.payment_status, self.payment_status.title())

    def __repr__(self):
        return f'<LoanPayment {self.id} Amount {self.amount}>'


# ─── Payment Receipt Model ────────────────────────────────────

class PaymentReceipt(db.Model):
    __tablename__ = 'payment_receipts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_payment_id = db.Column(db.Integer, db.ForeignKey('loan_payments.id'), nullable=True, index=True)

    receipt_number = db.Column(db.String(100), nullable=False, unique=True)
    receipt_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    pdf_filename = db.Column(db.String(255), nullable=False)
    pdf_original_filename = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentReceipt {self.id} {self.receipt_number}>'


# ─── Notification Model ───────────────────────────────────────

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    action_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id} {self.title}>'


# ─── Audit Log Model ───────────────────────────────────────────

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    action = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Polymorphic relationships (via string references)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=True)
    loan_payment_id = db.Column(db.Integer, db.ForeignKey('loan_payments.id'), nullable=True)

    # Relationships to specific entities
    document = db.relationship('Document', backref='audit_logs')
    loan = db.relationship('Loan', backref='audit_logs')
    loan_payment = db.relationship('LoanPayment', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.id} {self.action}>'


# ─── Reminder Preference Model ─────────────────────────────────

class UserReminderPreference(db.Model):
    __tablename__ = 'user_reminder_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    doc_days_before = db.Column(db.String(100), nullable=False, default='30,14,7,1')
    emi_days_before = db.Column(db.String(100), nullable=False, default='7,3,1,0')
    in_app_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_enabled = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserReminderPreference {self.id}>'


# ─── Government Application Model ─────────────────────────────────

class GovernmentApplication(db.Model):
    """Local tracking record for a user's government certificate application.

    This model does not submit applications to a government portal or verify
    official application status. Users must apply on the official site.
    """

    __tablename__ = 'government_applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True
    )

    service_type = db.Column(db.String(80), nullable=False, index=True)
    applicant_name = db.Column(db.String(150), nullable=False)
    district = db.Column(db.String(100), nullable=False)

    # draft = saved locally; submitted_by_user = user says they submitted
    # through the official portal; other statuses are locally recorded only.
    status = db.Column(
        db.String(30),
        nullable=False,
        default='draft',
        index=True
    )

    official_reference = db.Column(db.String(100), nullable=True, index=True)
    application_date = db.Column(db.Date, nullable=True)
    expected_completion_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    @property
    def status_display(self):
        labels = {
            'draft': 'Draft',
            'submitted_by_user': 'Submitted (user reported)',
            'in_progress': 'In Progress (not verified)',
            'completed': 'Completed (not verified)',
            'rejected': 'Rejected (not verified)',
            'cancelled': 'Cancelled',
        }
        return labels.get(self.status, self.status.replace('_', ' ').title())

    def __repr__(self):
        return (
            f'<GovernmentApplication {self.id} '
            f'{self.service_type} status={self.status}>'
        )


# ─── Global Dictionaries for Display ───────────────────────────

PAYMENT_STATUSES_DICT = dict(PAYMENT_STATUSES)
LOAN_STATUSES_DICT = dict(LOAN_STATUSES)
PAYMENT_METHODS_DICT = dict(PAYMENT_METHODS)