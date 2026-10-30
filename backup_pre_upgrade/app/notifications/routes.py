"""Notification centre routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
@login_required
def list_notifications():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '').strip()
    unread_only = request.args.get('unread', '').strip()

    query = Notification.query.filter_by(user_id=current_user.id)

    if category:
        query = query.filter_by(category=category)

    if unread_only == '1':
        query = query.filter_by(is_read=False)

    query = query.order_by(Notification.created_at.desc())
    notifications = query.paginate(page=page, per_page=20, error_out=False)

    return render_template('notifications/list.html',
                           notifications=notifications,
                           current_category=category,
                           unread_only=unread_only)


@notifications_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)

    notif.is_read = True
    db.session.commit()

    # Redirect to related resource if available
    if notif.related_document_id:
        return redirect(url_for('documents.view_document', doc_id=notif.related_document_id))
    elif notif.related_loan_id:
        return redirect(url_for('loans.view_loan', loan_id=notif.related_loan_id))

    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/<int:notif_id>/delete', methods=['POST'])
@login_required
def delete_notification(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)

    db.session.delete(notif)
    db.session.commit()
    flash('Notification deleted.', 'success')
    return redirect(url_for('notifications.list_notifications'))
