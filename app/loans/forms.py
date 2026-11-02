"""Loan forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, DateField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date

class LoanForm(FlaskForm):
    loan_type = SelectField('Loan Type', validators=[DataRequired()], choices=[])
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    interest_rate = DecimalField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=50)], places=2)
    loan_tenure_months = IntegerField('Loan Tenure (Months)', validators=[DataRequired(), NumberRange(min=1, max=360)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()], default=date.today)