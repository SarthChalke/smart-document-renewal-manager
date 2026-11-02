"""Settings routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, UserReminderPreference
from app.forms import RegistrationForm, LoginForm, ProfileForm, ChangePasswordForm, SettingsForm
from werkzeug.security import generate_password_hash, check_password_hash

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def settings():
    return render_template('settings.html')


@settings_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_settings():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        # Check email uniqueness
        existing = User.query.filter(User.email == form.email.data, User.id != current_user.id).first()
        if existing:
            flash('Email already in use.', 'danger')
        else:
            current_user.full_name = form.full_name.data
            current_user.email = form.email.data
            current_user.phone = form.phone.data
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('settings.profile_settings'))

    return render_template('settings/profile.html', form=form)


@settings_bp.route('/security', methods=['GET', 'POST'])
@login_required
def security_settings():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('settings.security_settings'))
        else:
            flash('Current password is incorrect.', 'danger')

    return render_template('settings/security.html', form=form)


@settings_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    preferences = UserReminderPreference.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        if not preferences:
            preferences = UserReminderPreference(user_id=current_user.id)
            db.session.add(preferences)

        # Update preferences
        doc_days = request.form.get('doc_days_before', '30,14,7,1')
        emi_days = request.form.get('emi_days_before', '7,3,1,0')

        preferences.doc_days_before = doc_days
        preferences.emi_days_before = emi_days
        preferences.in_app_enabled = 'in_app_enabled' in request.form
        preferences.email_enabled = 'email_enabled' in request.form

        db.session.commit()
        flash('Notification preferences updated.', 'success')
        return redirect(url_for('settings.notification_settings'))

    return render_template('settings/notifications.html', preferences=preferences)


@settings_bp.route('/data-export')
@login_required
def data_export():
    return render_template('settings/data_export.html')


@settings_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    # In production, add password confirmation here
    password = request.form.get('password', '')

    if not current_user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('settings.settings'))

    # Delete user data (cascade delete due to relationships)
    db.session.delete(current_user)
    db.session.commit()

    from flask_login import logout_user
    logout_user()

    flash('Account deleted successfully.', 'success')
    return redirect(url_for('auth.login'))


@settings_bp.route('/api/reminders')
@login_required
def api_reminders():
    preferences = UserReminderPreference.query.filter_by(user_id=current_user.id).first()

    if not preferences:
        return jsonify({})

    return jsonify({
        'doc_days_before': preferences.doc_days_before,
        'emi_days_before': preferences.emi_days_before,
        'in_app_enabled': preferences.in_app_enabled,
        'email_enabled': preferences.email_enabled
    })