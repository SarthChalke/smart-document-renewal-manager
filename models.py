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
    document_number = db.Column(db.String(100), index=True)
    issuing_authority = db.Column(db.String(200))
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date, index=True)
    holder_name = db.Column(db.String(150))
    notes = db.Column(db.Text)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    renewal_status = db.Column(db.String(50), default='Not Started')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to renewals
    renewals = db.relationship('DocumentRenewal', backref='document', lazy='dynamic',
                               cascade='all, delete-orphan', order_by='DocumentRenewal.created_at.desc()')

    @property
    def expiry_status(self):
        if self.renewal_status == 'Completed':
            return 'renewed'
        if not self.expiry_date:
            return 'no_expiry'
        today = date.today()
        days = (self.expiry_date - today).days
        if days < 0:
            return 'expired'
        elif days == 0:
            return 'expiring_today'
        elif days <= 30:
            return 'expiring_soon'
        else:
            return 'valid'

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def category_display(self):
        return DOCUMENT_CATEGORY_DICT.get(self.category, self.category.replace('_', ' ').title())

    @property
    def status_display(self):
        mapping = {
            'valid': 'Valid',
            'expiring_soon': 'Expiring Soon',
            'expiring_today': 'Expiring Today',
            'expired': 'Expired',
            'renewed': 'Renewed',
            'no_expiry': 'No Expiry Date',
        }
        return mapping.get(self.expiry_status, 'Unknown')

    @property
    def status_badge_class(self):
        mapping = {
            'valid': 'badge-valid',
            'expiring_soon': 'badge-expiring',
            'expiring_today': 'badge-today',
            'expired': 'badge-expired',
            'renewed': 'badge-renewed',
            'no_expiry': 'badge-secondary',
        }
        return mapping.get(self.expiry_status, 'badge-secondary')

    def __repr__(self):
        return f'<Document {self.title}>'


# ─── Document Renewal Model ──────────────────────────────────

class DocumentRenewal(db.Model):
    __tablename__ = 'document_renewals'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    application_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_completion_date = db.Column(db.Date)
    actual_renewal_date = db.Column(db.Date)
    previous_expiry_date = db.Column(db.Date)
    new_expiry_date = db.Column(db.Date)
    status = db.Column(db.String(50), nullable=False, default='Applied')  # Applied, In Progress, Completed, Rejected
    renewed_document_filename = db.Column(db.String(300))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_badge_class(self):
        mapping = {
            'Not Started': 'badge-secondary',
            'Applied': 'badge-warning',
            'In Progress': 'badge-info',
            'Completed': 'badge-success',
            'Rejected': 'badge-danger',
        }
        return mapping.get(self.status, 'badge-secondary')

    def __repr__(self):
        return f'<DocumentRenewal Doc={self.document_id} Status={self.status}>'


# ─── Loan Model ──────────────────────────────────────────────

class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_id_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., LN-202610-001
    loan_name = db.Column(db.String(200), nullable=False)
    loan_type = db.Column(db.String(50), nullable=False, index=True)
    lender_name = db.Column(db.String(200), nullable=False)
    loan_reference_number = db.Column(db.String(100), index=True)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    annual_interest_rate = db.Column(db.Numeric(5, 2), default=0.0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    tenure_months = db.Column(db.Integer, nullable=False)
    monthly_emi = db.Column(db.Numeric(15, 2), nullable=False)
    emi_due_day = db.Column(db.Integer, nullable=False)  # 1 - 31
    total_amount_payable = db.Column(db.Numeric(15, 2), nullable=False)
    next_emi_date = db.Column(db.Date, index=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active, completed, overdue, closed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    emi_schedules = db.relationship('EMISchedule', backref='loan', lazy='dynamic',
                                    cascade='all, delete-orphan', order_by='EMISchedule.installment_number.asc()')
    payments = db.relationship('LoanPayment', backref='loan', lazy='dynamic',
                               cascade='all, delete-orphan', order_by='LoanPayment.payment_date.desc()')

    @property
    def loan_type_display(self):
        return LOAN_TYPE_DICT.get(self.loan_type, self.loan_type.replace('_', ' ').title())

    @property
    def status_display(self):
        return LOAN_STATUS_DICT.get(self.status, self.status.title())

    @property
    def status_badge_class(self):
        mapping = {
            'active': 'badge-success',
            'completed': 'badge-primary',
            'overdue': 'badge-danger',
            'closed': 'badge-secondary',
        }
        return mapping.get(self.status, 'badge-secondary')

    @property
    def total_eligible_paid(self):
        """Sum of completed payments only. Pending, failed, cancelled do not count."""
        val = db.session.query(db.func.sum(LoanPayment.amount)).filter(
            LoanPayment.loan_id == self.id,
            LoanPayment.payment_status == 'completed'
        ).scalar()
        return Decimal(val or 0)

    @property
    def estimated_outstanding_principal(self):
        paid = self.total_eligible_paid
        principal = Decimal(self.principal_amount)
        return max(Decimal('0.00'), principal - paid)

    @property
    def repayment_progress_percent(self):
        principal = Decimal(self.principal_amount)
        if principal <= 0:
            return 100.0
        paid = self.total_eligible_paid
        pct = float((paid / principal) * 100)
        return min(100.0, round(pct, 1))

    @property
    def total_emis_count(self):
        return self.emi_schedules.count()

    @property
    def paid_emis_count(self):
        return self.emi_schedules.filter_by(status='paid').count()

    def __repr__(self):
        return f'<Loan {self.loan_id_code}: {self.loan_name}>'


# ─── EMI Schedule Model ──────────────────────────────────────

class EMISchedule(db.Model):
    __tablename__ = 'emi_schedules'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    installment_number = db.Column(db.Integer, nullable=False)
    scheduled_amount = db.Column(db.Numeric(15, 2), nullable=False)
    principal_component = db.Column(db.Numeric(15, 2), default=0.0)
    interest_component = db.Column(db.Numeric(15, 2), default=0.0)
    due_date = db.Column(db.Date, nullable=False, index=True)
    amount_paid = db.Column(db.Numeric(15, 2), default=Decimal('0.00'), nullable=False)
    remaining_amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default='upcoming', index=True)  # upcoming, due_today, paid, partially_paid, overdue
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per loan installment
    __table_args__ = (
        db.UniqueConstraint('loan_id', 'installment_number', name='uq_loan_installment'),
    )

    # Associated payments
    payments = db.relationship('LoanPayment', backref='emi_schedule', lazy='dynamic')

    @property
    def computed_status(self):
        if self.status == 'paid':
            return 'paid'
        if self.status == 'partially_paid' and self.remaining_amount <= 0:
            return 'paid'
        today = date.today()
        if self.amount_paid > 0 and self.remaining_amount > 0:
            return 'partially_paid'
        if self.due_date < today:
            return 'overdue'
        elif self.due_date == today:
            return 'due_today'
        return 'upcoming'

    @property
    def status_display(self):
        mapping = {
            'upcoming': 'Upcoming',
            'due_today': 'Due Today',
            'paid': 'Paid',
            'partially_paid': 'Partially Paid',
            'overdue': 'Overdue',
        }
        return mapping.get(self.status, self.status.title())

    @property
    def status_badge_class(self):
        mapping = {
            'upcoming': 'badge-info',
            'due_today': 'badge-warning',
            'paid': 'badge-success',
            'partially_paid': 'badge-partial',
            'overdue': 'badge-danger',
        }
        return mapping.get(self.status, 'badge-secondary')

    def __repr__(self):
        return f'<EMISchedule Loan={self.loan_id} #{self.installment_number} Due={self.due_date}>'


# ─── Loan Payment Model ──────────────────────────────────────

class LoanPayment(db.Model):
    __tablename__ = 'loan_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)
    emi_id = db.Column(db.Integer, db.ForeignKey('emi_schedules.id'), nullable=True, index=True)
    payment_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., PAY-202610-0001
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    payment_method = db.Column(db.String(50), nullable=False, default='Bank Transfer')
    transaction_reference = db.Column(db.String(100), index=True)
    payment_status = db.Column(db.String(20), nullable=False, default='completed', index=True)  # completed, pending, failed, cancelled
    receipt_filename = db.Column(db.String(300))  # Optional uploaded proof
    notes = db.Column(db.Text)
    is_partial = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 1-to-1 receipt
    receipt = db.relationship('PaymentReceipt', backref='payment', uselist=False, cascade='all, delete-orphan')

    @property
    def status_badge_class(self):
        mapping = {
            'completed': 'badge-success',
            'pending': 'badge-warning',
            'failed': 'badge-danger',
            'cancelled': 'badge-secondary',
        }
        return mapping.get(self.payment_status, 'badge-secondary')

    def __repr__(self):
        return f'<LoanPayment {self.payment_reference}: ₹{self.amount} ({self.payment_status})>'


# ─── Payment Receipt Model ───────────────────────────────────

class PaymentReceipt(db.Model):
    __tablename__ = 'payment_receipts'

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., RCT-202610-0001
    payment_id = db.Column(db.Integer, db.ForeignKey('loan_payments.id'), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_name = db.Column(db.String(200), nullable=False)
    lender_name = db.Column(db.String(200), nullable=False)
    emi_number = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_reference = db.Column(db.String(100))
    payment_status = db.Column(db.String(20), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    pdf_filename = db.Column(db.String(300))

    def __repr__(self):
        return f'<PaymentReceipt {self.receipt_number} Amount={self.amount}>'


# ─── Notification Model ──────────────────────────────────────

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # doc_expiring, doc_expired, emi_due, emi_overdue, payment_recorded, renewal_update
    is_read = db.Column(db.Boolean, default=False, index=True)
    related_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    related_loan_id = db.Column(db.Integer, db.ForeignKey('loans.id', ondelete='SET NULL'), nullable=True)
    related_emi_id = db.Column(db.Integer, db.ForeignKey('emi_schedules.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def icon_class(self):
        mapping = {
            'doc_expiring': 'bi-clock-history text-warning',
            'doc_expired': 'bi-exclamation-octagon text-danger',
            'renewal_update': 'bi-arrow-repeat text-info',
            'emi_due': 'bi-calendar-event text-warning',
            'emi_overdue': 'bi-exclamation-triangle text-danger',
            'payment_recorded': 'bi-check-circle text-primary',
        }
        return mapping.get(self.category, 'bi-bell text-primary')

    def __repr__(self):
        return f'<Notification {self.title}>'


# ─── Audit Log Model ─────────────────────────────────────────

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type} #{self.entity_id}>'


# ─── User Reminder Preference Model ──────────────────────────

class UserReminderPreference(db.Model):
    __tablename__ = 'user_reminder_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    doc_days_before = db.Column(db.String(100), default='30,14,7,1', nullable=False)
    emi_days_before = db.Column(db.String(100), default='7,3,1,0', nullable=False)
    in_app_enabled = db.Column(db.Boolean, default=True)
    email_enabled = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def doc_days_list(self):
        return [int(x.strip()) for x in self.doc_days_before.split(',') if x.strip().isdigit()]

    @property
    def emi_days_list(self):
        return [int(x.strip()) for x in self.emi_days_before.split(',') if x.strip().isdigit()]

    def __repr__(self):
        return f'<UserReminderPreference User={self.user_id}>'



# ─── Maharashtra Government Certificate Application Model ───

class GovernmentApplication(db.Model):
    """Local tracking record for a user's government certificate application.

    This model does not submit applications to a government portal or verify
    official application status. Those features require an approved integration.
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
        default=datetime.utcnow,
        onupdate=datetime.utcnow
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
