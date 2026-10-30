
import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

# Read database URL from the environment.
database_url = os.environ.get("DATABASE_URL")

# Support PostgreSQL URLs supplied with the older postgres:// prefix.
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    if not SECRET_KEY:
        SECRET_KEY = (
            "local-development-only-change-this-secret"
        )

    # Use the hosted PostgreSQL URL in production.
    SQLALCHEMY_DATABASE_URI = database_url or (
        "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Local folders; these are not persistent on Vercel.
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    DOCUMENTS_FOLDER = os.path.join(
        UPLOAD_FOLDER, "documents"
    )
    RECEIPTS_FOLDER = os.path.join(
        UPLOAD_FOLDER, "receipts"
    )

    # Vercel has a 4.5 MB request payload limit.
    # Use a lower limit to leave room for multipart overhead.
    MAX_CONTENT_LENGTH = (
        4 * 1024 * 1024
        if os.environ.get("VERCEL")
        else 16 * 1024 * 1024
    )

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    # Set this in your local .env if Tesseract is installed.
    # Vercel will need a compatible Linux Tesseract binary
    # and its trained-data files for image OCR to work.
    TESSERACT_CMD = os.environ.get(
        "TESSERACT_CMD", "tesseract"
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.environ.get("VERCEL") == "1"
    )

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

    UPLOAD_FOLDER = os.path.join(basedir, "test_uploads")
    DOCUMENTS_FOLDER = os.path.join(
        UPLOAD_FOLDER, "documents"
    )
    RECEIPTS_FOLDER = os.path.join(
        UPLOAD_FOLDER, "receipts"
    )
    SERVER_NAME = "localhost.localdomain"
