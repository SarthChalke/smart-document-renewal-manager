
import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "change-this-secret-key"
    )

    # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://smartdoc_user:Sarth%4019@localhost:5432/smartdoc_db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload Directories
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, "documents")
    RECEIPTS_FOLDER = os.path.join(UPLOAD_FOLDER, "receipts")

    # Maximum upload size: 16 MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    # OCR Settings
    TESSERACT_CMD = os.environ.get(
        "TESSERACT_CMD",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True

    # In-memory SQLite database for automated tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    WTF_CSRF_ENABLED = False

    UPLOAD_FOLDER = os.path.join(basedir, "test_uploads")
    DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, "documents")
    RECEIPTS_FOLDER = os.path.join(UPLOAD_FOLDER, "receipts")

    SERVER_NAME = "localhost.localdomain"
