
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env for local development.
# Vercel production settings come from environment variables.
basedir = Path(__file__).resolve().parent
load_dotenv(basedir / ".env")

IS_VERCEL = os.environ.get("VERCEL") == "1"
IS_PRODUCTION = (
    IS_VERCEL
    or os.environ.get("FLASK_ENV") == "production"
    or os.environ.get("APP_ENV") == "production"
)

# Database configuration
database_url = os.environ.get("DATABASE_URL", "").strip()

# Support older PostgreSQL URL prefixes.
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

# Do not silently use SQLite in production.
if IS_PRODUCTION and not database_url:
    raise RuntimeError(
        "DATABASE_URL must be configured in production."
    )

# Require a strong secret in production.
secret_key = os.environ.get("SECRET_KEY")

if IS_PRODUCTION and not secret_key:
    raise RuntimeError(
        "SECRET_KEY must be configured in production."
    )

if not IS_PRODUCTION and not secret_key:
    secret_key = "local-development-only-change-this-secret"


class Config:
    SECRET_KEY = secret_key

    SQLALCHEMY_DATABASE_URI = database_url or (
        "sqlite:///" + str(basedir / "instance" / "app.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Local paths only. Use persistent object storage in production.
    UPLOAD_FOLDER = str(basedir / "uploads")
    DOCUMENTS_FOLDER = str(
        basedir / "uploads" / "documents"
    )
    RECEIPTS_FOLDER = str(
        basedir / "uploads" / "receipts"
    )

    # Keep request sizes below Vercel's 4.5 MB request limit.
    MAX_CONTENT_LENGTH = (
        4 * 1024 * 1024 if IS_VERCEL
        else 16 * 1024 * 1024
    )

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    # Configure a valid executable path if Tesseract is installed.
    TESSERACT_CMD = os.environ.get(
        "TESSERACT_CMD", "tesseract"
    )

    # Session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    # Enable CSRF protection for form submissions.
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

    UPLOAD_FOLDER = str(basedir / "test_uploads")
    DOCUMENTS_FOLDER = str(
        basedir / "test_uploads" / "documents"
    )
    RECEIPTS_FOLDER = str(
        basedir / "test_uploads" / "receipts"
    )
    SERVER_NAME = "localhost.localdomain"
