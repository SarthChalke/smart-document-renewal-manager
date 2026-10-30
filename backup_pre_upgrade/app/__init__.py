from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.documents.routes import documents_bp
    from app.renewals.routes import renewals_bp
    from app.loans.routes import loans_bp
    from app.emi.routes import emi_bp
    from app.payments.routes import payments_bp
    from app.notifications.routes import notifications_bp
    from app.reminders.routes import reminders_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(renewals_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(emi_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reminders_bp)

    # Create database tables
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

        # Initialize scheduler
        from app.services.reminder_service import init_scheduler
        if not app.config.get('TESTING'):
            init_scheduler(app)

    # Context processor for notification count
    @app.context_processor
    def inject_notification_count():
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.models import Notification
            unread_count = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            return dict(unread_notification_count=unread_count)
        return dict(unread_notification_count=0)

    return app
