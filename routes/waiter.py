"""Waiter blueprint: tables, customers, order creation (POS), serving."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.order import Order, OrderItem, KitchenOrder, Payment, Invoice
from models.table import RestaurantTable, Reservation
from models.user import Customer, User
from models.menu import MenuItem, Category
from models.settings import RestaurantSettings
from utils.helpers import log_activity, generate_order_number, generate_invoice_number, notify_role
from utils.validators import sanitize_int, sanitize_float
from datetime import datetime

bp = Blueprint("waiter", __name__, url_prefix="/waiter")


@bp.before_request
def require_waiter():
    if not current_user.is_authenticated or current_user.role.name not in ("ADMIN", "MANAGER", "WAITER"):
        abort(403)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    tables = RestaurantTable.query.order_by(RestaurantTable.table_number).all()
    active = Order.query.filter(Order.order_status.in_(["new", "accepted", "preparing"])).all()
    ready = Order.query.filter_by(order_status="ready").all()
    served = Order.query.filter_by(order_status="served").all()
    customers = Customer.query.join(User).filter(User.status == "active").limit(10).all()
    return render_template("waiter/dashboard.html",
        tables=tables, active=active, ready=ready, served=served, customers=customers)


@bp.route("/pos")
@bp.route("/pos/<int:table_id>")
def pos(table_id=None):
    categories = Category.query.filter_by(status="active").order_by(Category.display_order).all()
    items = MenuItem.query.filter_by(availability="available", status="active").all()
    table = RestaurantTable.query.get(table_id) if table_id else None
    return render_template("waiter/pos.html", categories=categories, items=items, table=table)


@bp.route("/orders/create", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    table_id = sanitize_int(data.get("table_id"))
    order_type = data.get("order_type", "dine_in")
    customer_id = sanitize_int(data.get("customer_id")) or None
    items = data.get("items", [])
    special = data.get("special_instructions", "")
    if not items:
        return jsonify({"ok": False, "error": "No items."}), 400

    table = RestaurantTable.query.get(table_id) if table_id else None
    settings = RestaurantSettings.query.first()
    tax_rate = settings.tax_rate if settings else 10.0

    order = Order(
        order_number=generate_order_number(),
        order_type=order_type,
        customer_id=customer_id,
        table_id=table.id if table else None,
        waiter_id=current_user.staff_profile.id if current_user.staff_profile else None,
        special_instructions=special,
        order_status="new",
        payment_status="pending",
    )
    db.session.add(order)
    db.session.flush()

    subtotal = 0.0
    for it in items:
        mi = MenuItem.query.get(sanitize_int(it.get("id")))
        if not mi:
            continue
        qty = sanitize_int(it.get("qty"), 1)
        unit = mi.final_price
        disc = mi.discount or 0
        subtotal += unit * qty
        oi = OrderItem(
            order_id=order.id, menu_item_id=mi.id, quantity=qty,
            unit_price=mi.price, discount=disc, special_instructions=it.get("note", ""),
        )
        db.session.add(oi)

    discount_total = round(subtotal * 0, 2)  # item-level discounts already applied
    tax = round(subtotal * tax_rate / 100.0, 2)
    delivery = 0.0
    if order_type == "delivery" and settings:
        delivery = settings.delivery_charges or 0
    total = round(subtotal + tax + delivery, 2)
    order.subtotal = round(subtotal, 2)
    order.discount = discount_total
    order.tax = tax
    order.delivery_charges = delivery
    order.total = total

    # Kitchen order record
    ko = KitchenOrder(order_id=order.id, status="new")
    db.session.add(ko)

    if table:
        table.status = "occupied"
        table.current_order_id = order.id

    db.session.commit()
    log_activity(current_user, "order_created", "orders", request.remote_addr)
    notify_role("CHEF", "New Order", f"Order {order.order_number} received from {table.table_number if table else order_type}.", "info", "/chef/dashboard")
    notify_role("ADMIN", "New Order", f"Order {order.order_number} created.", "info")
    return jsonify({"ok": True, "order_id": order.id, "order_number": order.order_number})


@bp.route("/orders")
def orders():
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter(Order.order_status == status)
    else:
        query = query.filter(Order.order_status.in_(["new", "accepted", "preparing", "ready", "served"]))
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("waiter/orders.html", orders=orders)


@bp.route("/orders/<int:oid>/serve", methods=["POST"])
def serve_order(oid):
    order = Order.query.get_or_404(oid)
    order.order_status = "served"
    for it in order.items:
        it.status = "served"
    db.session.commit()
    log_activity(current_user, "order_served", "orders", request.remote_addr)
    return jsonify({"ok": True})


@bp.route("/orders/<int:oid>/complete", methods=["POST"])
def complete_order(oid):
    order = Order.query.get_or_404(oid)
    order.order_status = "completed"
    if order.table:
        order.table.status = "available"
        order.table.current_order_id = None
    db.session.commit()
    log_activity(current_user, "order_completed", "orders", request.remote_addr)
    return jsonify({"ok": True})


@bp.route("/orders/<int:oid>/pay", methods=["GET", "POST"])
def pay_order(oid):
    order = Order.query.get_or_404(oid)
    if request.method == "POST":
        method = request.form.get("method", "cash")
        order.payment_method = method
        order.payment_status = "paid"
        pay = Payment(order_id=order.id, amount=order.total, method=method,
                      status="paid", created_by=current_user.id)
        db.session.add(pay)
        if not order.invoice:
            inv = Invoice(invoice_number=generate_invoice_number(), order_id=order.id,
                          subtotal=order.subtotal, discount=order.discount, tax=order.tax,
                          delivery_charges=order.delivery_charges, total=order.total)
            db.session.add(inv)
        db.session.commit()
        flash("Payment recorded.", "success")
        return redirect(url_for("waiter.orders"))
    return render_template("waiter/pay_order.html", order=order)


@bp.route("/tables")
def tables():
    tables = RestaurantTable.query.order_by(RestaurantTable.table_number).all()
    return render_template("waiter/tables.html", tables=tables)


@bp.route("/customers")
def customers():
    customers = Customer.query.join(User).filter(User.status == "active").order_by(Customer.created_at.desc()).all()
    return render_template("waiter/customers.html", customers=customers)
