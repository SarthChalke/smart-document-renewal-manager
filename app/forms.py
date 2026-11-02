"""Flask-WTF forms for all blueprints."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, DateField, PasswordField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Optional, Email, Length, EqualTo, NumberRange


class RegistrationForm(FlaskForm):
    """User registration form."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = StringField('Password', validators=[DataRequired(), Length(min=6)], render_kw={'type': 'password'})
    confirm_password = StringField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ], render_kw={'type': 'password'})


class LoginForm(FlaskForm):
    """User login form."""
    username = StringField('Username or Email', validators=[DataRequired(), Length(max=80)])
    password = StringField('Password', validators=[DataRequired()], render_kw={'type': 'password'})
    remember = BooleanField('Remember me', default=True)


class ProfileForm(FlaskForm):
    """User profile form."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])


class ChangePasswordForm(FlaskForm):
    """Change password form."""
    current_password = StringField('Current Password', validators=[DataRequired()], render_kw={'type': 'password'})
    new_password = StringField('New Password', validators=[DataRequired(), Length(min=6)], render_kw={'type': 'password'})
    confirm_password = StringField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ], render_kw={'type': 'password'})


class DocumentUploadForm(FlaskForm):
    """Document upload form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', validators=[DataRequired()], choices=[])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issuing_authority = StringField('Issuing Authority', validators=[Optional(), Length(max=150)])
    holder_name = StringField('Holder Name', validators=[Optional(), Length(max=150)])
    issue_date = DateField('Issue Date', format='%Y-%m-%d', validators=[Optional()])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=4000)])
    document_file = StringField('File', validators=[DataRequired()])  # FileField handled in routes


class DocumentEditForm(FlaskForm):
    """Document edit form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', validators=[DataRequired()], choices=[])


class DocumentOCRForm(FlaskForm):
    """Document OCR scan form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', validators=[DataRequired()], choices=[])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issuing_authority = StringField('Issuing Authority', validators=[Optional(), Length(max=150)])
    holder_name = StringField('Holder Name', validators=[Optional(), Length(max=150)])
    issue_date = DateField('Issue Date', format='%Y-%m-%d', validators=[Optional()])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=4000)])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issuing_authority = StringField('Issuing Authority', validators=[Optional(), Length(max=150)])
    holder_name = StringField('Holder Name', validators=[Optional(), Length(max=150)])
    issue_date = DateField('Issue Date', format='%Y-%m-%d', validators=[Optional()])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=4000)])


class GovernmentApplicationForm(FlaskForm):
    """Government certificate application form."""
    applicant_name = StringField('Applicant Name', validators=[DataRequired(), Length(max=150)])
    district = StringField('District', validators=[DataRequired(), Length(max=100)])
    application_date = DateField('Application Date', format='%Y-%m-%d', validators=[Optional()])
    expected_completion_date = DateField('Expected Completion Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=4000)])


class GovernmentApplicationStatusForm(FlaskForm):
    """Form for updating application status."""
    status = SelectField('Status', choices=[
        ('draft', 'Draft'),
        ('submitted_by_user', 'Submitted (User)'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])


class LoanForm(FlaskForm):
    """Loan creation form."""
    loan_type = SelectField('Loan Type', validators=[DataRequired()], choices=[])
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    interest_rate = DecimalField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=50)], places=2)
    loan_tenure_months = IntegerField('Loan Tenure (Months)', validators=[DataRequired(), NumberRange(min=1, max=360)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])


class EMICalculationForm(FlaskForm):
    """EMI calculation form."""
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    interest_rate = DecimalField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=50)], places=2)
    loan_tenure_months = IntegerField('Loan Tenure (Months)', validators=[DataRequired(), NumberRange(min=1, max=360)])


class LoanPaymentForm(FlaskForm):
    """Loan payment form."""
    amount = DecimalField('Payment Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    payment_date = DateField('Payment Date', format='%Y-%m-%d', validators=[Optional()])
    payment_method = SelectField('Payment Method', validators=[DataRequired()], choices=[
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('Debit Card', 'Debit Card'),
        ('Credit Card', 'Credit Card'),
        ('Other', 'Other')
    ])