"""Input validation helpers."""
import re
from werkzeug.datastructures import FileStorage


def is_valid_email(email):
    if not email:
        return False
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


def is_valid_phone(phone):
    if not phone:
        return False
    return re.match(r"^[\d\s\+\-\(\)]{6,20}$", phone) is not None


def is_safe_string(value, max_length=255):
    if value is None:
        return True
    return isinstance(value, str) and len(value) <= max_length


def allowed_image(filename, allowed=None):
    if not filename:
        return False
    if allowed is None:
        allowed = {"png", "jpg", "jpeg", "gif", "webp", "svg", "ico"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def validate_image_upload(file, max_size_mb=16):
    """Validate an uploaded image file. Returns (ok, error_message)."""
    if file is None or not isinstance(file, FileStorage) or not file.filename:
        return False, "No file provided."
    if not allowed_image(file.filename):
        return False, "Unsupported image format."
    try:
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > max_size_mb * 1024 * 1024:
            return False, f"File too large (max {max_size_mb}MB)."
    except Exception:
        return False, "Unable to read file."
    return True, ""


def sanitize_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sanitize_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
