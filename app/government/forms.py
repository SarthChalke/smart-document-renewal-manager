"""Government forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, DateField, FileField
from wtforms.validators import DataRequired, Optional


class GovernmentApplicationForm(FlaskForm):
    """Form for applying for government certificates."""
    applicant_name = StringField('Applicant Name', validators=[DataRequired()])
    district = StringField('District', validators=[DataRequired()])
    application_date = DateField('Application Date', format='%Y-%m-%d', validators=[Optional()])
    expected_completion_date = DateField('Expected Completion Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])


class GovernmentApplicationStatusForm(FlaskForm):
    """Form for updating application status."""
    status = SelectField('Status', choices=[
        ('draft', 'Draft'),
        ('submitted_by_user', 'Submitted (User)'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], validators=[DataRequired()]
    )
    notes = TextAreaField('Notes', validators=[Optional()])