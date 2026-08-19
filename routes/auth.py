"""Authentication: login, logout, password change, account settings."""
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash
)
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models.user import User, Staff, Customer, Role
from utils.helpers import log_activity
from datetime import datetime

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home_for_role(current_user))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.status == "active":
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_activity(user, "login", "auth", request.remote_addr)
            name = user.staff_profile.full_name if user.staff_profile else user.username
            flash("Welcome back, " + name + "!", "success")
            return redirect(_home_for_role(user))
        flash("Invalid username or password.", "danger")
    return render_template("auth/login.html")


def _home_for_role(user):
    role = user.role.name if user.role else "CUSTOMER"
    mapping = {
        "ADMIN": "admin.dashboard",
        "MANAGER": "manager.dashboard",
        "WAITER": "waiter.dashboard",
        "CHEF": "chef.dashboard",
        "CUSTOMER": "customer.dashboard",
    }
    return url_for(mapping.get(role, "public.home"))


@bp.route("/logout")
@login_required
def logout():
    log_activity(current_user, "logout", "auth", request.remote_addr)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not current_user.check_password(current):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 6:
            flash("New password must be at least 6 characters.", "danger")
        elif new != confirm:
            flash("New passwords do not match.", "danger")
        else:
            current_user.set_password(new)
            db.session.commit()
            log_activity(current_user, "change_password", "auth", request.remote_addr)
            flash("Password updated successfully.", "success")
            return redirect(url_for("auth.change_password"))
    return render_template("auth/change_password.html")
