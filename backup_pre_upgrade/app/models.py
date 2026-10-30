from datetime import datetime, date
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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

    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    loans = db.relationship('Loan', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    reminder_preferences = db.relationship('UserReminderPreference', backref='owner', lazy='dynamic',
                                           cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


DOCUMENT_CATEGORIES = [
    ('identity', 'Identity Documents'),
    ('driving_licence', 'Driving Licence'),
    ('vehicle', 'Vehicle Documents'),
    ('insurance', 'Insurance'),
    ('education', 'Education Certificates'),
    ('marksheets', 'Mark Sheets'),
    ('medical', 'Medical Documents'),
    ('employment', 'Employment Documents'),
    ('personal', 'Personal Documents'),
    ('other', 'Other Documents'),
]

DOCUMENT_CATEGORY_DICT = dict(DOCUMENT_CATEGORIES)


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, index=True)
    document_number = db.Column(db.String(100))
    issue_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date, index=True)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    renewal_history = db.relationship('DocumentRenewalHistory', backref='document', lazy='dynamic',
                                      cascade='all, delete-orphan',
                                      order_by='DocumentRenewalHistory.renewed_at.desc()')

    @property
    def expiry_status(self):
        if not self.expiry_date:
            return 'no_expiry'
        today = date.today()
        days_remaining = (self.expiry_date - today).days
        if days_remaining < 0:
            return 'expired'
        elif days_remaining <= 30:
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
        return DOCUMENT_CATEGORY_DICT.get(self.category, self.category)

    @property
    def status_badge_class(self):
        status_map = {
            'valid': 'bg-success',
            'expiring_soon': 'bg-warning text-dark',
            'expired': 'bg-danger',
            'no_expiry': 'bg-secondary',
        }
        return status_map.get(self.expiry_status, 'bg-secondary')

    @property
    def status_display(self):
        display_map = {
            'valid': 'Valid',
            'expiring_soon': 'Expiring Soon',
            'expired': 'Expired',
            'no_expiry': 'No Expiry Date',
        }
        return display_map.get(self.expiry_status, 'Unknown')

    def __repr__(self):
        return f'<Document {self.title}>'


class DocumentRenewalHistory(db.Model):
    __tablename__ = 'document_renewal_history'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    previous_expiry_date = db.Column(db.Date)
    new_expiry_date = db.Column(db.Date)
    previous_issue_date = db.Column(db.Date)
    new_issue_date = db.Column(db.Date)
    renewal_document_filename = db.Column(db.String(300))
    notes = db.Column(db.Text)
    renewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RenewalHistory Document={self.document_id} at {self.renewed_at}>'


LOAN_TYPES = [
    ('personal', 'Personal Loan'),
    ('home', 'Home Loan'),
    ('education', 'Education Loan'),
    ('vehicle', 'Vehicle Loan'),
    ('business', 'Business Loan'),
    ('gold', 'Gold Loan'),
    ('other', 'Other Loan'),
]

LOAN_TYPE_DICT = dict(LOAN_TYPES)

LOAN_STATUSES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('defaulted', 'Defaulted'),
    ('closed', 'Closed'),
]

LOAN_STATUS_DICT = dict(LOAN_STATUSES)


class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    loan_name = db.Column(db.String(200), nullable=False)
    lender_name = db.Column(db.String(200), nullable=False)
    loan_type = db.Column(db.String(50), nullable=False, index=True)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2))  # Optional
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # Optional
    monthly_emi = db.Column(db.Numeric(15, 2), nullable=False)
    emi_due_day = db.Column(db.Integer, nullable=False)  # 1-31
    next_emi_date = db.Column(db.Date, index=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    emi_payments = db.relationship('EMIPayment', backref='loan', lazy='dynamic',
                                   cascade='all, delete-orphan',
                                   order_by='EMIPayment.due_date.desc()')

    @property
    def loan_type_display(self):
        return LOAN_TYPE_DICT.get(self.loan_type, self.loan_type)

    @property
    def status_display(self):
        return LOAN_STATUS_DICT.get(self.status, self.status)

    @property
    def status_badge_class(self):
        status_map = {
            'active': 'bg-success',
            'completed': 'bg-primary',
            'defaulted': 'bg-danger',
            'closed': 'bg-secondary',
        }
        return status_map.get(self.status, 'bg-secondary')

    @property
    def total_paid(self):
        result = db.session.query(
            db.func.sum(EMIPayment.amount)
        ).filter(
            EMIPayment.loan_id == self.id,
            EMIPayment.status == 'paid'
        ).scalar()
        return result or 0

    @property
    def total_emis_paid(self):
        return EMIPayment.query.filter_by(loan_id=self.id, status='paid').count()

    @property
    def outstanding_estimate(self):
        """Estimate only - not a lender-approved balance."""
        paid = float(self.total_paid)
        principal = float(self.principal_amount)
        if paid > 0:
            return max(0, principal - paid)
        return None  # Not enough data

    def __repr__(self):
        return f'<Loan {self.loan_name}>'


EMI_STATUSES = [
    ('upcoming', 'Upcoming'),
    ('due_today', 'Due Today'),
    ('paid', 'Paid'),
    ('overdue', 'Overdue'),
    ('pending', 'Pending'),
]

EMI_STATUS_DICT = dict(EMI_STATUSES)


class EMIPayment(db.Model):
    __tablename__ = 'emi_payments'

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='upcoming', index=True)
    payment_date = db.Column(db.Date)
    transaction_reference = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one EMI per loan per due date
    __table_args__ = (
        db.UniqueConstraint('loan_id', 'due_date', name='uq_loan_due_date'),
    )

    @property
    def status_display(self):
        return EMI_STATUS_DICT.get(self.status, self.status)

    @property
    def status_badge_class(self):
        status_map = {
            'upcoming': 'bg-info',
            'due_today': 'bg-warning text-dark',
            'paid': 'bg-success',
            'overdue': 'bg-danger',
            'pending': 'bg-secondary',
        }
        return status_map.get(self.status, 'bg-secondary')

    @property
    def computed_status(self):
        """Re-compute status based on current date."""
        if self.status == 'paid':
            return 'paid'
        today = date.today()
        if self.due_date < today:
            return 'overdue'
        elif self.due_date == today:
            return 'due_today'
        else:
            return 'upcoming'

    def __repr__(self):
        return f'<EMIPayment Loan={self.loan_id} Due={self.due_date}>'


NOTIFICATION_CATEGORIES = [
    ('doc_expiring', 'Document Expiring Soon'),
    ('doc_expired', 'Document Expired'),
    ('doc_renewal', 'Document Renewal Reminder'),
    ('emi_due_soon', 'EMI Due Soon'),
    ('emi_due_today', 'EMI Due Today'),
    ('emi_overdue', 'EMI Overdue'),
    ('payment_updated', 'Payment Status Updated'),
]


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    related_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    related_loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'))
    related_emi_id = db.Column(db.Integer, db.ForeignKey('emi_payments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships for navigation
    related_document = db.relationship('Document', foreign_keys=[related_document_id])
    related_loan = db.relationship('Loan', foreign_keys=[related_loan_id])
    related_emi = db.relationship('EMIPayment', foreign_keys=[related_emi_id])

    def __repr__(self):
        return f'<Notification {self.title}>'


class UserReminderPreference(db.Model):
    __tablename__ = 'user_reminder_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reminder_type = db.Column(db.String(50), nullable=False)  # 'document' or 'emi'
    days_before = db.Column(db.String(100), nullable=False, default='7,3,1,0')
    email_enabled = db.Column(db.Boolean, default=False)
    in_app_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'reminder_type', name='uq_user_reminder_type'),
    )

    @property
    def days_list(self):
        return [int(d.strip()) for d in self.days_before.split(',') if d.strip().isdigit()]

    def __repr__(self):
        return f'<ReminderPref User={self.user_id} Type={self.reminder_type}>'
