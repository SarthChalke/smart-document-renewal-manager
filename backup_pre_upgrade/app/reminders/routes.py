"""Reminder and settings routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models import UserReminderPreference
from app.forms import ReminderPreferenceForm
from app.services.reminder_service import trigger_reminders_manually

reminders_bp = Blueprint('reminders', __name__, url_prefix='/reminders')


@reminders_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ReminderPreferenceForm()

    doc_pref = UserReminderPreference.query.filter_by(
        user_id=current_user.id, reminder_type='document'
    ).first()
    emi_pref = UserReminderPreference.query.filter_by(
        user_id=current_user.id, reminder_type='emi'
    ).first()

    if form.validate_on_submit():
        # Parse and validate days
        try:
            doc_days = ','.join([str(int(d.strip())) for d in form.doc_days_before.data.split(',') if d.strip()])
            emi_days = ','.join([str(int(d.strip())) for d in form.emi_days_before.data.split(',') if d.strip()])
        except ValueError:
            flash('Please enter valid comma-separated numbers for reminder days.', 'danger')
            return render_template('reminders/settings.html', form=form)

        if not doc_pref:
            doc_pref = UserReminderPreference(user_id=current_user.id, reminder_type='document')
            db.session.add(doc_pref)
        doc_pref.days_before = doc_days
        doc_pref.email_enabled = form.doc_email_enabled.data
        doc_pref.in_app_enabled = form.doc_in_app_enabled.data

        if not emi_pref:
            emi_pref = UserReminderPreference(user_id=current_user.id, reminder_type='emi')
            db.session.add(emi_pref)
        emi_pref.days_before = emi_days
        emi_pref.email_enabled = form.emi_email_enabled.data
        emi_pref.in_app_enabled = form.emi_in_app_enabled.data

        db.session.commit()
        flash('Reminder preferences saved.', 'success')
        return redirect(url_for('reminders.settings'))

    # Pre-fill form
    if doc_pref:
        form.doc_days_before.data = doc_pref.days_before
        form.doc_email_enabled.data = doc_pref.email_enabled
        form.doc_in_app_enabled.data = doc_pref.in_app_enabled
    if emi_pref:
        form.emi_days_before.data = emi_pref.days_before
        form.emi_email_enabled.data = emi_pref.email_enabled
        form.emi_in_app_enabled.data = emi_pref.in_app_enabled

    return render_template('reminders/settings.html', form=form)


@reminders_bp.route('/trigger', methods=['POST'])
@login_required
def trigger():
    """Manual trigger for development."""
    result = trigger_reminders_manually(current_app._get_current_object())
    flash(result, 'success')
    return redirect(url_for('reminders.settings'))
