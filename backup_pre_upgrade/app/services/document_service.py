"""Document management service."""
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename
from flask import current_app


ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
ALLOWED_MIMES = {
    'application/pdf', 'image/jpeg', 'image/png', 'image/jpg'
}

# File signatures (magic bytes)
FILE_SIGNATURES = {
    b'%PDF': 'pdf',
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG': 'png',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file(file_storage):
    """Validate file extension, MIME type, and content."""
    errors = []

    if not file_storage or not file_storage.filename:
        errors.append('No file selected.')
        return errors

    filename = file_storage.filename
    if not allowed_file(filename):
        errors.append('File type not allowed. Only PDF, JPG, JPEG, PNG files are accepted.')
        return errors

    # Check MIME type
    mime = file_storage.content_type or mimetypes.guess_type(filename)[0]
    if mime and mime not in ALLOWED_MIMES:
        errors.append(f'Invalid MIME type: {mime}')

    # Check file content (magic bytes)
    header = file_storage.read(8)
    file_storage.seek(0)

    if header:
        valid_sig = False
        for sig, ext_type in FILE_SIGNATURES.items():
            if header.startswith(sig):
                valid_sig = True
                break
        if not valid_sig:
            errors.append('File content does not match expected format.')

    return errors


def save_uploaded_file(file_storage, user_id):
    """Save an uploaded file securely and return (filename, original_filename, file_size, mime_type)."""
    original_filename = secure_filename(file_storage.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'

    # Generate unique filename
    unique_name = f"{user_id}_{uuid.uuid4().hex}.{ext}"

    upload_folder = current_app.config['UPLOAD_FOLDER']
    user_folder = os.path.join(upload_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    filepath = os.path.join(user_folder, unique_name)
    file_storage.save(filepath)

    file_size = os.path.getsize(filepath)
    mime_type = file_storage.content_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

    return unique_name, original_filename, file_size, mime_type


def get_file_path(filename, user_id):
    """Get the full path to a user's uploaded file."""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_folder, str(user_id), secure_filename(filename))
    if os.path.exists(filepath):
        return filepath
    return None


def delete_uploaded_file(filename, user_id):
    """Delete an uploaded file."""
    filepath = get_file_path(filename, user_id)
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except OSError:
            return False
    return False
