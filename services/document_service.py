import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename
from config import Config

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
ALLOWED_MIMES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/jpg'
}

FILE_SIGNATURES = {
    b'%PDF': 'pdf',
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG': 'png',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_uploaded_file(file_storage):
    """Validate file extension, MIME type, size, and magic bytes."""
    errors = []

    if not file_storage or not file_storage.filename:
        errors.append('No file selected.')
        return errors

    filename = file_storage.filename
    if not allowed_file(filename):
        errors.append('File type not allowed. Please upload a PDF, JPG, JPEG, or PNG file.')
        return errors

    # Check MIME type
    mime = file_storage.content_type or mimetypes.guess_type(filename)[0]
    if mime and mime.lower() not in ALLOWED_MIMES:
        errors.append(f'Invalid file MIME type: {mime}')

    # Check magic bytes
    header = file_storage.read(8)
    file_storage.seek(0)

    if header:
        valid_sig = False
        for sig, _ in FILE_SIGNATURES.items():
            if header.startswith(sig):
                valid_sig = True
                break
        if not valid_sig:
            errors.append('File content does not match allowed format (PDF or valid image expected).')

    return errors


def save_document_file(file_storage, user_id):
    """Save document file in user-isolated folder under uploads/documents/."""
    os.makedirs(Config.DOCUMENTS_FOLDER, exist_ok=True)

    original_filename = secure_filename(file_storage.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
    unique_filename = f"doc_{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    
    file_path = os.path.join(Config.DOCUMENTS_FOLDER, unique_filename)
    file_storage.save(file_path)

    file_size = os.path.getsize(file_path)
    mime_type = file_storage.content_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

    return unique_filename, original_filename, file_size, mime_type


def save_receipt_file(file_storage, user_id):
    """Save payment receipt attachment in uploads/receipts/."""
    os.makedirs(Config.RECEIPTS_FOLDER, exist_ok=True)

    original_filename = secure_filename(file_storage.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
    unique_filename = f"rcpt_{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    
    file_path = os.path.join(Config.RECEIPTS_FOLDER, unique_filename)
    file_storage.save(file_path)

    return unique_filename


def get_document_path(filename):
    """Get full filesystem path for a document file."""
    if not filename:
        return None
    safe_name = os.path.basename(filename)
    path = os.path.join(Config.DOCUMENTS_FOLDER, safe_name)
    if os.path.isfile(path):
        return path
    return None


def get_receipt_path(filename):
    """Get full filesystem path for a receipt file."""
    if not filename:
        return None
    safe_name = os.path.basename(filename)
    path = os.path.join(Config.RECEIPTS_FOLDER, safe_name)
    if os.path.isfile(path):
        return path
    return None


def delete_document_file(filename):
    """Delete a document file from storage."""
    path = get_document_path(filename)
    if path and os.path.exists(path):
        try:
            os.remove(path)
            return True
        except OSError:
            return False
    return False

