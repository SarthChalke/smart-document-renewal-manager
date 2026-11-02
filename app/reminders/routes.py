"""Reminders routes."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

reminders_bp = Blueprint('reminders', __name__)


@reminders_bp.route('/')
@login_required
def index():
    """Reminders page."""
    return render_template('reminders/index.html')