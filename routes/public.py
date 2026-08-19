"""Public website blueprint: home, about, menu, services, reservation, contact, auth."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_user, current_user, login_required
from extensions import db
from models.user import User, Customer, Role
from models.menu import Category, MenuItem, Review
from models.settings import (
    Banner, Service, AboutContent, Offer, RestaurantSettings, HeaderSettings, FooterSettings,
)
from models.table import Reservation, RestaurantTable
from utils.helpers import log_activity, save_uploaded_file
from utils.validators import is_valid_email, is_valid_phone, sanitize_int
from datetime import datetime, date, time

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    banners = Banner.query.filter_by(status="active").order_by(Banner.display_order).all()
    featured = MenuItem.query.filter_by(featured=True, status="active", availability="available").limit(8).all()
    categories = Category.query.filter_by(status="active").order_by(Category.display_order).limit(6).all()
    services = Service.query.filter_by(status="active").order_by(Service.display_order).all()
    popular = (
        db.session.query(MenuItem).filter_by(status="active", availability="available")
        .order_by(MenuItem.rating.desc()).limit(6).all()
    )
    offers = Offer.query.filter_by(status="active").limit(3).all()
    reviews = Review.query.filter_by(status="approved").order_by(Review.created_at.desc()).limit(6).all()
    about = AboutContent.query.first()
    return render_template("public/home.html", banners=banners, featured=featured,
                           categories=categories, services=services, popular=popular,
                           offers=offers, reviews=reviews, about=about)


@bp.route("/about")
def about():
    about = AboutContent.query.first()
    services = Service.query.filter_by(status="active").order_by(Service.display_order).all()
    reviews = Review.query.filter_by(status="approved").order_by(Review.created_at.desc()).limit(6).all()
    return render_template("public/about.html", about=about, services=services, reviews=reviews)


@bp.route("/menu")
def menu():
    categories = Category.query.filter_by(status="active").order_by(Category.display_order).all()
    cat_id = request.args.get("category", "")
    q = request.args.get("q", "")
    sort = request.args.get("sort", "")
    query = MenuItem.query.filter_by(status="active")
    if cat_id:
        query = query.filter_by(category_id=sanitize_int(cat_id))
    if q:
        query = query.filter(MenuItem.name.ilike(f"%{q}%"))
    if sort == "price_asc":
        query = query.order_by(MenuItem.price.asc())
    elif sort == "price_desc":
        query = query.order_by(MenuItem.price.desc())
    elif sort == "rating":
        query = query.order_by(MenuItem.rating.desc())
    else:
        query = query.order_by(MenuItem.display_order)
    items = query.all()
    return render_template("public/menu.html", categories=categories, items=items,
                           cat_id=cat_id, q=q, sort=sort)


@bp.route("/services")
def services():
    services = Service.query.filter_by(status="active").order_by(Service.display_order).all()
    return render_template("public/services.html", services=services)


@bp.route("/reservation", methods=["GET", "POST"])
def reservation():
    tables = RestaurantTable.query.filter_by(status="available").all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        rdate = _parse_date(request.form.get("date"))
        rtime = _parse_time(request.form.get("time"))
        guests = sanitize_int(request.form.get("guests", 2))
        table_id = sanitize_int(request.form.get("table_id")) or None
        special = request.form.get("special_request", "")
        customer_id = current_user.customer_profile.id if current_user.is_authenticated and current_user.customer_profile else None
        r = Reservation(customer_id=customer_id, customer_name=name, phone=phone, email=email,
                        reservation_date=rdate, reservation_time=rtime, guests=guests,
                        table_id=table_id, special_request=special, status="pending")
        db.session.add(r)
        db.session.commit()
        log_activity(current_user, "reservation_created", "reservations", request.remote_addr)
        flash("Reservation submitted successfully! We will confirm shortly.", "success")
        return redirect(url_for("public.reservation"))
    return render_template("public/reservation.html", tables=tables)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # In a full system this would email; we log it as an activity for admin visibility.
        name = request.form.get("name", "")
        log_activity(None, "contact_message", "contact", request.remote_addr,
                    details=f"From {name}: {request.form.get('message','')}")
        flash("Thank you for contacting us! We will get back to you soon.", "success")
        return redirect(url_for("public.contact"))
    return render_template("public/contact.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.status == "active":
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_activity(user, "login", "auth", request.remote_addr)
            if user.role.name == "CUSTOMER":
                return redirect(url_for("customer.dashboard"))
            return redirect(url_for("public.home"))
        flash("Invalid credentials.", "danger")
    return render_template("public/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not all([full_name, username, email, password]):
            flash("All fields are required.", "danger")
            return render_template("public/register.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("public/register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("public/register.html")
        role = Role.query.filter_by(name="CUSTOMER").first()
        user = User(username=username, email=email, role_id=role.id, status="active")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        customer = Customer(user_id=user.id, full_name=full_name, phone=phone,
                            profile_image="uploads/customers/default.png")
        db.session.add(customer)
        db.session.commit()
        login_user(user)
        flash("Account created! Welcome to our restaurant.", "success")
        return redirect(url_for("customer.dashboard"))
    return render_template("public/register.html")


@bp.route("/privacy")
def privacy():
    return render_template("public/privacy.html")


@bp.route("/terms")
def terms():
    return render_template("public/terms.html")


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
