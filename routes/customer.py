"""Customer blueprint: website customer portal."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.user import Customer, User
from models.order import Order
from models.table import Reservation, RestaurantTable as Table
from models.menu import MenuItem, Review
from utils.helpers import log_activity, save_uploaded_file
from utils.validators import is_valid_email, is_valid_phone, sanitize_int
from datetime import datetime, date, time

bp = Blueprint("customer", __name__, url_prefix="/customer")


@bp.before_request
def require_customer():
    if not current_user.is_authenticated or current_user.role.name != "CUSTOMER":
        abort(403)
    if not current_user.customer_profile:
        abort(403)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    customer = current_user.customer_profile
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).limit(5).all()
    reservations = Reservation.query.filter_by(customer_id=customer.id).order_by(Reservation.reservation_date.desc()).limit(5).all()
    total_spent = sum(o.total for o in Order.query.filter_by(customer_id=customer.id, payment_status="paid").all())
    return render_template("customer/dashboard.html", customer=customer, orders=orders,
                           reservations=reservations, total_spent=total_spent)


@bp.route("/orders")
def orders():
    customer = current_user.customer_profile
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/orders.html", orders=orders)


@bp.route("/orders/<int:oid>")
def order_detail(oid):
    customer = current_user.customer_profile
    order = Order.query.filter_by(id=oid, customer_id=customer.id).first_or_404()
    return render_template("customer/order_detail.html", order=order)


@bp.route("/reservations", methods=["GET", "POST"])
def reservations():
    customer = current_user.customer_profile
    if request.method == "POST":
        r = Reservation(
            customer_id=customer.id,
            customer_name=request.form.get("customer_name", customer.full_name),
            phone=request.form.get("phone", customer.phone),
            email=request.form.get("email", current_user.email),
            reservation_date=_parse_date(request.form.get("reservation_date")),
            reservation_time=_parse_time(request.form.get("reservation_time")),
            guests=sanitize_int(request.form.get("guests", 2)),
            table_id=sanitize_int(request.form.get("table_id")) or None,
            special_request=request.form.get("special_request", ""),
            status="pending",
        )
        db.session.add(r)
        db.session.commit()
        log_activity(current_user, "reservation_created", "reservations", request.remote_addr)
        flash("Reservation submitted. We will confirm shortly.", "success")
        return redirect(url_for("customer.reservations"))
    reservations = Reservation.query.filter_by(customer_id=customer.id).order_by(Reservation.reservation_date.desc()).all()
    tables = Table.query.filter_by(status="available").all()
    return render_template("customer/reservations.html", reservations=reservations, tables=tables, customer=customer)


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    customer = current_user.customer_profile
    if request.method == "POST":
        customer.full_name = request.form.get("full_name", customer.full_name)
        customer.phone = request.form.get("phone", customer.phone)
        customer.address = request.form.get("address", customer.address)
        current_user.email = request.form.get("email", current_user.email)
        if request.files.get("profile_image"):
            path = save_uploaded_file(request.files["profile_image"], "customers")
            if path:
                customer.profile_image = path
        pw = request.form.get("password", "")
        if pw:
            if len(pw) < 6:
                flash("Password must be at least 6 characters.", "danger")
                return redirect(url_for("customer.profile"))
            current_user.set_password(pw)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("customer.profile"))
    return render_template("customer/profile.html", customer=customer)


@bp.route("/reviews", methods=["POST"])
def add_review():
    customer = current_user.customer_profile
    menu_item_id = sanitize_int(request.form.get("menu_item_id"))
    rating = sanitize_int(request.form.get("rating"), 5)
    comment = request.form.get("comment", "")
    order_id = sanitize_int(request.form.get("order_id")) or None
    review = Review(customer_id=customer.id, menu_item_id=menu_item_id or None,
                    order_id=order_id, rating=rating, comment=comment, status="pending")
    db.session.add(review)
    db.session.commit()
    flash("Thank you! Your review is pending approval.", "success")
    return redirect(request.referrer or url_for("customer.dashboard"))


def _parse_date(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return date.today()


def _parse_time(value):
    if not value:
        return time(19, 0)
    try:
        return datetime.strptime(value, "%H:%M").time()
    except Exception:
        return time(19, 0)
