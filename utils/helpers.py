"""General helper utilities: file uploads, money formatting, order numbers, etc."""
import os
import secrets
import string
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from extensions import db
from models.settings import Notification, ActivityLog


def save_uploaded_file(file, subfolder, filename=None):
    """Securely save an uploaded file under static/uploads/<subfolder>.
    Returns the relative path (e.g. uploads/products/abc.png) or None."""
    from utils.validators import validate_image_upload

    ok, err = validate_image_upload(file)
    if not ok:
        return None
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    if filename is None:
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{generate_token(12)}.{ext}"
    else:
        filename = secure_filename(filename)
    dest = os.path.join(upload_dir, filename)
    # Avoid overwriting: append token if exists
    if os.path.exists(dest):
        filename = f"{generate_token(8)}_{filename}"
        dest = os.path.join(upload_dir, filename)
    file.save(dest)
    return f"uploads/{subfolder}/{filename}"


def generate_token(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_order_number():
    from models.order import Order
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand = generate_token(4).upper()
    return f"ORD-{date_part}-{rand}"


def generate_invoice_number():
    date_part = datetime.utcnow().strftime("%Y%m")
    rand = generate_token(4).upper()
    return f"INV-{date_part}-{rand}"


def generate_purchase_number():
    date_part = datetime.utcnow().strftime("%Y%m")
    rand = generate_token(4).upper()
    return f"PUR-{date_part}-{rand}"


def format_currency(amount, symbol="$"):
    try:
        return f"{symbol}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def log_activity(user, action, module, details=None, ip=None):
    """Record an activity log entry."""
    try:
        entry = ActivityLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action,
            module=module,
            details=details,
            ip_address=ip,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()


def notify(user_id, title, message, ntype="info", link=None):
    """Create a notification for a user."""
    try:
        n = Notification(
            user_id=user_id, title=title, message=message, type=ntype, link=link
        )
        db.session.add(n)
        db.session.commit()
    except Exception:
        db.session.rollback()


def notify_role(role_name, title, message, ntype="info", link=None):
    """Notify all active users with a given role name."""
    from models.user import User, Role
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return
    users = User.query.filter_by(role_id=role.id, status="active").all()
    for u in users:
        notify(u.id, title, message, ntype, link)
