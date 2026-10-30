from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, TextAreaField, SelectField,
                     DateField, DecimalField, IntegerField, BooleanField, SubmitField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, ValidationError
from app.models import User, DOCUMENT_CATEGORIES, LOAN_TYPES, LOAN_STATUSES


# ─── Auth Forms ───────────────────────────────────────────────

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')


# ─── Document Forms ──────────────────────────────────────────

class DocumentUploadForm(FlaskForm):
    title = StringField('Document Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category = SelectField('Category', choices=DOCUMENT_CATEGORIES, validators=[DataRequired()])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issue_date = DateField('Issue Date', validators=[Optional()], format='%Y-%m-%d')
    expiry_date = DateField('Expiry Date', validators=[Optional()], format='%Y-%m-%d')
    file = FileField('Document File',
                     validators=[DataRequired(), FileAllowed(['pdf', 'jpg', 'jpeg', 'png'],
                                                              'Only PDF, JPG, JPEG, PNG files are allowed.')])
    submit = SubmitField('Upload Document')


class DocumentEditForm(FlaskForm):
    title = StringField('Document Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category = SelectField('Category', choices=DOCUMENT_CATEGORIES, validators=[DataRequired()])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issue_date = DateField('Issue Date', validators=[Optional()], format='%Y-%m-%d')
    expiry_date = DateField('Expiry Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Update Document')


class DocumentOCRForm(FlaskForm):
    title = StringField('Document Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category = SelectField('Category', choices=DOCUMENT_CATEGORIES, validators=[DataRequired()])
    document_number = StringField('Document Number', validators=[Optional(), Length(max=100)])
    issue_date = DateField('Issue Date', validators=[Optional()], format='%Y-%m-%d')
    expiry_date = DateField('Expiry Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Confirm & Save')


class DocumentRenewForm(FlaskForm):
    new_issue_date = DateField('New Issue Date', validators=[Optional()], format='%Y-%m-%d')
    new_expiry_date = DateField('New Expiry Date', validators=[Optional()], format='%Y-%m-%d')
    file = FileField('Renewed Document',
                     validators=[Optional(), FileAllowed(['pdf', 'jpg', 'jpeg', 'png'],
                                                          'Only PDF, JPG, JPEG, PNG files are allowed.')])
    notes = TextAreaField('Renewal Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Renew Document')


# ─── Loan Forms ──────────────────────────────────────────────

class LoanForm(FlaskForm):
    loan_name = StringField('Loan Name', validators=[DataRequired(), Length(max=200)])
    lender_name = StringField('Bank / Lender Name', validators=[DataRequired(), Length(max=200)])
    loan_type = SelectField('Loan Type', choices=LOAN_TYPES, validators=[DataRequired()])
    principal_amount = DecimalField('Principal Amount (₹)', validators=[DataRequired(), NumberRange(min=1)], places=2)
    interest_rate = DecimalField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)], places=2)
    start_date = DateField('Loan Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('Loan End Date', validators=[Optional()], format='%Y-%m-%d')
    monthly_emi = DecimalField('Monthly EMI (₹)', validators=[DataRequired(), NumberRange(min=1)], places=2)
    emi_due_day = IntegerField('EMI Due Day (1-31)', validators=[DataRequired(), NumberRange(min=1, max=31)])
    next_emi_date = DateField('Next EMI Due Date', validators=[DataRequired()], format='%Y-%m-%d')
    status = SelectField('Loan Status', choices=LOAN_STATUSES, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Save Loan')


# ─── EMI Forms ───────────────────────────────────────────────

class EMIGenerateForm(FlaskForm):
    num_months = IntegerField('Number of Months', validators=[DataRequired(), NumberRange(min=1, max=360)],
                              default=12)
    submit = SubmitField('Generate EMI Schedule')


class EMIPaymentForm(FlaskForm):
    payment_date = DateField('Payment Date', validators=[DataRequired()], format='%Y-%m-%d')
    transaction_reference = StringField('Transaction Reference', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Mark as Paid')


# ─── Reminder Settings ───────────────────────────────────────

class ReminderPreferenceForm(FlaskForm):
    doc_days_before = StringField('Document Reminder Days (comma-separated)',
                                  validators=[DataRequired()], default='30,14,7,1')
    doc_email_enabled = BooleanField('Email Reminders for Documents')
    doc_in_app_enabled = BooleanField('In-App Reminders for Documents', default=True)
    emi_days_before = StringField('EMI Reminder Days (comma-separated)',
                                  validators=[DataRequired()], default='7,3,1,0')
    emi_email_enabled = BooleanField('Email Reminders for EMIs')
    emi_in_app_enabled = BooleanField('In-App Reminders for EMIs', default=True)
    submit = SubmitField('Save Preferences')
