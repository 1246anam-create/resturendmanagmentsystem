"""Manager blueprint: restaurant operations focus."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.order import Order, Payment, OrderItem
from models.table import RestaurantTable, Reservation
from models.user import Customer, Staff, User, Role
from models.inventory import InventoryItem, Supplier, Purchase
from models.menu import MenuItem
from utils.helpers import log_activity, generate_invoice_number
from utils.validators import sanitize_int, sanitize_float
from datetime import datetime, date, timedelta

bp = Blueprint("manager", __name__, url_prefix="/manager")


@bp.before_request
def require_manager():
    if not current_user.is_authenticated or current_user.role.name not in ("ADMIN", "MANAGER"):
        abort(403)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    today = date.today()
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).all()
    today_sales = sum(o.total for o in today_orders if o.payment_status == "paid")
    tables = RestaurantTable.query.all()
    reservations = Reservation.query.filter_by(status="pending").all()
    low_stock = InventoryItem.query.filter(InventoryItem.status.in_(["low_stock", "out_of_stock"])).all()
    staff = Staff.query.join(User).filter(User.status == "active").all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    popular = (
        db.session.query(MenuItem.name, db.func.sum(OrderItem.quantity))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .group_by(MenuItem.name).order_by(db.func.sum(OrderItem.quantity).desc()).limit(5).all()
    )
    popular_food = [{"name": p[0], "qty": int(p[1] or 0)} for p in popular]
    return render_template("manager/dashboard.html",
        today_sales=today_sales, today_orders=len(today_orders),
        tables=tables, reservations=reservations, low_stock=low_stock,
        staff=staff, recent_orders=recent_orders, popular_food=popular_food)


@bp.route("/orders")
def orders():
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter(Order.order_status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("manager/orders.html", orders=orders)


@bp.route("/orders/<int:oid>/status", methods=["POST"])
def order_status(oid):
    order = Order.query.get_or_404(oid)
    order.order_status = request.form.get("status", order.order_status)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/tables")
def tables():
    tables = RestaurantTable.query.order_by(RestaurantTable.table_number).all()
    return render_template("manager/tables.html", tables=tables)


@bp.route("/reservations")
def reservations():
    status = request.args.get("status", "")
    query = Reservation.query
    if status:
        query = query.filter(Reservation.status == status)
    reservations = query.order_by(Reservation.reservation_date).all()
    tables = RestaurantTable.query.all()
    return render_template("manager/reservations.html", reservations=reservations, tables=tables)


@bp.route("/reservations/<int:rid>/status", methods=["POST"])
def reservation_status(rid):
    r = Reservation.query.get_or_404(rid)
    action = request.form.get("action")
    if action == "confirm":
        r.status = "confirmed"
        if r.table:
            r.table.status = "reserved"
    elif action == "cancel":
        r.status = "cancelled"
        if r.table and r.table.status == "reserved":
            r.table.status = "available"
    elif action == "complete":
        r.status = "completed"
        if r.table and r.table.status == "reserved":
            r.table.status = "available"
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/customers")
def customers():
    customers = Customer.query.join(User).filter(User.status == "active").order_by(Customer.created_at.desc()).all()
    return render_template("manager/customers.html", customers=customers)


@bp.route("/inventory")
def inventory():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template("manager/inventory.html", items=items)


@bp.route("/suppliers")
def suppliers():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template("manager/suppliers.html", suppliers=suppliers)


@bp.route("/purchases")
def purchases():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template("manager/purchases.html", purchases=purchases)


@bp.route("/reports")
def reports():
    start_month = date.today().replace(day=1)
    orders = Order.query.filter(Order.created_at >= start_month).all()
    revenue = sum(o.total for o in orders if o.payment_status == "paid")
    order_count = len(orders)
    return render_template("manager/reports.html", revenue=revenue, order_count=order_count,
                           orders=orders[:20])


@bp.route("/staff")
def staff():
    staff = Staff.query.join(User).filter(User.role.has(Role.name != "ADMIN")).all()
    return render_template("manager/staff.html", staff=staff)
