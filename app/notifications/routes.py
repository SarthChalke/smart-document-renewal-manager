"""Notifications routes."""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models import Notification

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/')
@login_required
def index():
    """List notifications."""
    page = request.args.get('page', 1, type=int)
    unread_only = request.args.get('unread', 'false') == 'true'

    query = Notification.query.filter_by(user_id=current_user.id)

    if unread_only:
        query = query.filter_by(is_read=False)

    notifications = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Mark all as read if requested
    if request.method == 'POST':
        Notification.query.filter_by(
            user_id=current_user.id, is_read=False
        ).update({'is_read': True})
        db.session.commit()
        return redirect(url_for('notifications.index'))

    return render_template('notifications/index.html', notifications=notifications)


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()

    notification.is_read = True
    db.session.commit()

    return redirect(request.args.get('next', url_for('notifications.index')))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {'is_read': True}
    )
    db.session.commit()

    return redirect(request.args.get('next', url_for('notifications.index')))


@notifications_bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete(notification_id):
    """Delete a notification."""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()

    db.session.delete(notification)
    db.session.commit()

    return redirect(url_for('notifications.index'))