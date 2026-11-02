from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─── Government Certificate Type Model ───────────────────────

class GovernmentCertificateType(db.Model):
    __tablename__ = 'government_certificate_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)

    # Portal information
    portal_url = db.Column(db.String(500), nullable=True)
    portal_description = db.Column(db.String(200), nullable=True)

    # Processing time
    processing_days_min = db.Column(db.Integer, default=7)
    processing_days_max = db.Column(db.Integer, default=30)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    requires_authentication = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requirements = db.relationship(
        'GovernmentCertificateRequirement',
        backref='certificate_type',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<GovernmentCertificateType {self.name}>'


# ─── Government Certificate Requirement Model ───────────────────

class GovernmentCertificateRequirement(db.Model):
    __tablename__ = 'government_certificate_requirements'

    id = db.Column(db.Integer, primary_key=True)
    certificate_type_id = db.Column(
        db.Integer,
        db.ForeignKey('government_certificate_types.id'),
        nullable=False,
        index=True
    )

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Document specifications
    document_type = db.Column(db.String(50), nullable=False, default='pdf')  # pdf, image, both
    max_file_size = db.Column(db.BigInteger, default=5 * 1024 * 1024)  # 5MB
    allowed_extensions = db.Column(db.String(100), default='pdf,png,jpg,jpeg')

    # Mandatory or optional
    is_mandatory = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(50), default='pending')  # pending, uploaded, verified

    # Fee information
    fee_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    fee_description = db.Column(db.String(200), nullable=True)

    # Order in application form
    order = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<GovernmentCertificateRequirement {self.name}>'


# ─── Government Application Document Model ──────────────────────

class GovernmentApplicationDocument(db.Model):
    __tablename__ = 'government_application_documents'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('government_applications.id'),
        nullable=False,
        index=True
    )
    requirement_id = db.Column(
        db.Integer,
        db.ForeignKey('government_certificate_requirements.id'),
        nullable=False,
        index=True
    )

    # File information
    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)

    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, uploaded, verified
    uploaded_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = db.relationship(
        'GovernmentApplication',
        backref=db.backref('documents', lazy='dynamic')
    )
    requirement = db.relationship(
        'GovernmentCertificateRequirement',
        backref=db.backref('application_documents', lazy='dynamic')
    )

    def __repr__(self):
        return f'<GovernmentApplicationDocument {self.id}>'


# ─── Government Application Fee Model ──────────────────────────

class GovernmentApplicationFee(db.Model):
    __tablename__ = 'government_application_fees'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('government_applications.id'),
        nullable=False,
        index=True
    )

    fee_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, waived
    payment_reference = db.Column(db.String(100), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = db.relationship(
        'GovernmentApplication',
        backref=db.backref('fee', lazy=True)
    )

    def __repr__(self):
        return f'<GovernmentApplicationFee {self.id}>'


# ─── Government Application Status History Model ─────────────────

class GovernmentApplicationStatusHistory(db.Model):
    __tablename__ = 'government_application_status_history'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('government_applications.id'),
        nullable=False,
        index=True
    )

    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    application = db.relationship(
        'GovernmentApplication',
        backref=db.backref('status_history', lazy='dynamic')
    )
    user = db.relationship(
        'User',
        backref=db.backref('government_application_status_history', lazy='dynamic')
    )

    def __repr__(self):
        return f'<GovernmentApplicationStatusHistory {self.id}>'