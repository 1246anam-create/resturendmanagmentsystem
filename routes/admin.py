"""Admin blueprint: full control panel for the restaurant system."""
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
)
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Staff, Customer, Role, Permission
from models.menu import Category, MenuItem, Review
from models.order import Order, OrderItem, KitchenOrder, Payment, Invoice, Delivery
from models.table import RestaurantTable, Reservation
from models.inventory import InventoryItem, InventoryTransaction, Supplier, Purchase, PurchaseItem
from models.settings import (
    Service, Banner, AboutContent, HeaderSettings, FooterSettings,
    RestaurantSettings, ThemeSettings, Notification, ActivityLog, Offer,
)
from utils.auth import permission_required, role_required, create_default_roles_and_permissions
from utils.helpers import (
    save_uploaded_file, log_activity, notify, notify_role,
    generate_order_number, generate_invoice_number, generate_purchase_number,
)
from utils.validators import is_valid_email, is_valid_phone, sanitize_int, sanitize_float
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import os

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def require_admin():
    if not current_user.is_authenticated or current_user.role.name != "ADMIN":
        abort(403)


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    today = date.today()
    start_of_month = today.replace(day=1)
    orders = Order.query
    today_orders = orders.filter(db.func.date(Order.created_at) == today).count()
    month_orders = orders.filter(Order.created_at >= start_of_month).all()
    today_revenue = sum(
        o.total for o in orders.filter(db.func.date(Order.created_at) == today).all()
        if o.payment_status == "paid"
    )
    month_revenue = sum(o.total for o in month_orders if o.payment_status == "paid")
    total_customers = Customer.query.count()
    total_staff = Staff.query.count()
    available = RestaurantTable.query.filter_by(status="available").count()
    occupied = RestaurantTable.query.filter_by(status="occupied").count()
    pending_res = Reservation.query.filter_by(status="pending").count()
    pending_orders = Order.query.filter(Order.order_status.in_(["new", "accepted", "preparing"])).count()
    low_stock = InventoryItem.query.filter(InventoryItem.status.in_(["low_stock", "out_of_stock"])).count()

    # Chart data: last 7 days sales
    daily = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rev = sum(o.total for o in orders.filter(db.func.date(Order.created_at) == d).all() if o.payment_status == "paid")
        daily.append({"label": d.strftime("%a"), "value": round(rev, 2)})

    # Popular food
    popular = (
        db.session.query(MenuItem.name, db.func.sum(OrderItem.quantity).label("qty"))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .group_by(MenuItem.name).order_by(db.func.sum(OrderItem.quantity).desc())
        .limit(5).all()
    )
    popular_food = [{"name": p[0], "qty": int(p[1] or 0)} for p in popular]

    # Payment methods
    pm = (
        db.session.query(Order.payment_method, db.func.count(Order.id))
        .group_by(Order.payment_method).all()
    )
    payment_methods = [{"name": p[0].replace("_", " ").title(), "value": p[1]} for p in pm]

    stats = dict(
        total_orders=Order.query.count(),
        today_orders=today_orders,
        today_revenue=today_revenue,
        month_revenue=month_revenue,
        total_customers=total_customers,
        total_staff=total_staff,
        available=available,
        occupied=occupied,
        pending_res=pending_res,
        pending_orders=pending_orders,
        low_stock=low_stock,
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats, daily=daily, popular_food=popular_food,
        payment_methods=payment_methods,
    )

# ===========================================================================
# STAFF
# ===========================================================================
@bp.route("/staff")
def staff():
    q = request.args.get("q", "")
    role = request.args.get("role", "")
    query = Staff.query.join(User)
    if q:
        query = query.filter(
            db.or_(Staff.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"),
                   Staff.phone.ilike(f"%{q}%"))
        )
    if role:
        query = query.filter(User.role.has(Role.name == role))
    staff = query.order_by(Staff.created_at.desc()).all()
    roles = Role.query.all()
    return render_template("admin/staff.html", staff=staff, roles=roles)


@bp.route("/staff/add", methods=["GET", "POST"])
def staff_add():
    roles = Role.query.filter(Role.name != "CUSTOMER").all()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role_id = sanitize_int(request.form.get("role_id"))
        if not all([full_name, username, email, password, role_id]):
            flash("All fields are required.", "danger")
            return render_template("admin/staff_form.html", staff=None, roles=roles)
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("admin/staff_form.html", staff=None, roles=roles)
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("admin/staff_form.html", staff=None, roles=roles)
        user = User(username=username, email=email, role_id=role_id, status="active")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        image = None
        if request.files.get("profile_image"):
            image = save_uploaded_file(request.files["profile_image"], "staff")
        s = Staff(
            user_id=user.id, full_name=full_name,
            phone=request.form.get("phone", ""),
            address=request.form.get("address", ""),
            profile_image=image or "uploads/staff/default.png",
            joining_date=_parse_date(request.form.get("joining_date")) or date.today(),
            emergency_contact=request.form.get("emergency_contact", ""),
            notes=request.form.get("notes", ""),
        )
        db.session.add(s)
        db.session.commit()
        log_activity(current_user, "staff_added", "staff", request.remote_addr)
        flash("Staff member added.", "success")
        return redirect(url_for("admin.staff"))
    return render_template("admin/staff_form.html", staff=None, roles=roles)


@bp.route("/staff/<int:sid>/edit", methods=["GET", "POST"])
def staff_edit(sid):
    s = Staff.query.get_or_404(sid)
    roles = Role.query.filter(Role.name != "CUSTOMER").all()
    if request.method == "POST":
        s.full_name = request.form.get("full_name", "").strip()
        s.phone = request.form.get("phone", "")
        s.address = request.form.get("address", "")
        s.emergency_contact = request.form.get("emergency_contact", "")
        s.notes = request.form.get("notes", "")
        s.user.email = request.form.get("email", "").strip()
        s.user.role_id = sanitize_int(request.form.get("role_id"))
        s.user.status = request.form.get("status", "active")
        if request.files.get("profile_image"):
            path = save_uploaded_file(request.files["profile_image"], "staff")
            if path:
                s.profile_image = path
        pw = request.form.get("password", "")
        if pw:
            s.user.set_password(pw)
        db.session.commit()
        log_activity(current_user, "staff_updated", "staff", request.remote_addr)
        flash("Staff member updated.", "success")
        return redirect(url_for("admin.staff"))
    return render_template("admin/staff_form.html", staff=s, roles=roles)


@bp.route("/staff/<int:sid>/toggle", methods=["POST"])
def staff_toggle(sid):
    s = Staff.query.get_or_404(sid)
    s.user.status = "inactive" if s.user.status == "active" else "active"
    db.session.commit()
    return jsonify({"ok": True, "status": s.user.status})


@bp.route("/staff/<int:sid>/delete", methods=["POST"])
def staff_delete(sid):
    s = Staff.query.get_or_404(sid)
    db.session.delete(s.user)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# ROLES & PERMISSIONS
# ===========================================================================
@bp.route("/roles")
def roles():
    roles = Role.query.all()
    permissions = Permission.query.order_by(Permission.name).all()
    return render_template("admin/roles.html", roles=roles, permissions=permissions)


@bp.route("/roles/<int:rid>/permissions", methods=["POST"])
def role_permissions_update(rid):
    role = Role.query.get_or_404(rid)
    if role.is_system and role.name == "ADMIN":
        return jsonify({"ok": False, "error": "Cannot modify admin permissions."}), 400
    perm_ids = request.form.getlist("permissions")
    role.permissions = []
    for pid in perm_ids:
        perm = Permission.query.get(sanitize_int(pid))
        if perm:
            role.permissions.append(perm)
    db.session.commit()
    return jsonify({"ok": True})

# ===========================================================================
# CUSTOMERS
# ===========================================================================
@bp.route("/customers")
def customers():
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    query = Customer.query.join(User)
    if q:
        query = query.filter(
            db.or_(Customer.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"),
                   Customer.phone.ilike(f"%{q}%"))
        )
    if status:
        query = query.filter(User.status == status)
    customers = query.order_by(Customer.created_at.desc()).all()
    return render_template("admin/customers.html", customers=customers)


@bp.route("/customers/<int:cid>/toggle", methods=["POST"])
def customer_toggle(cid):
    c = Customer.query.get_or_404(cid)
    c.user.status = "inactive" if c.user.status == "active" else "active"
    db.session.commit()
    return jsonify({"ok": True, "status": c.user.status})


@bp.route("/customers/<int:cid>/delete", methods=["POST"])
def customer_delete(cid):
    c = Customer.query.get_or_404(cid)
    db.session.delete(c.user)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# CATEGORIES
# ===========================================================================
@bp.route("/categories")
def categories():
    cats = Category.query.order_by(Category.display_order).all()
    return render_template("admin/categories.html", categories=cats)


@bp.route("/categories/add", methods=["GET", "POST"])
def category_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Category name is required.", "danger")
            return render_template("admin/category_form.html", category=None)
        slug = name.lower().replace(" ", "-")
        image = None
        if request.files.get("image"):
            image = save_uploaded_file(request.files["image"], "categories")
        cat = Category(
            name=name, slug=slug, description=request.form.get("description", ""),
            image=image, display_order=sanitize_int(request.form.get("display_order", 0)),
            status=request.form.get("status", "active"),
        )
        db.session.add(cat)
        db.session.commit()
        log_activity(current_user, "category_added", "menu", request.remote_addr)
        flash("Category added.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=None)


@bp.route("/categories/<int:cid>/edit", methods=["GET", "POST"])
def category_edit(cid):
    cat = Category.query.get_or_404(cid)
    if request.method == "POST":
        cat.name = request.form.get("name", "").strip()
        cat.description = request.form.get("description", "")
        cat.display_order = sanitize_int(request.form.get("display_order", 0))
        cat.status = request.form.get("status", "active")
        if request.files.get("image"):
            path = save_uploaded_file(request.files["image"], "categories")
            if path:
                cat.image = path
        db.session.commit()
        log_activity(current_user, "category_updated", "menu", request.remote_addr)
        flash("Category updated.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=cat)


@bp.route("/categories/<int:cid>/delete", methods=["POST"])
def category_delete(cid):
    cat = Category.query.get_or_404(cid)
    if cat.items.count() > 0:
        return jsonify({"ok": False, "error": "Remove menu items first."}), 400
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# MENU ITEMS
# ===========================================================================
@bp.route("/menu")
def menu():
    q = request.args.get("q", "")
    cat = request.args.get("category", "")
    avail = request.args.get("availability", "")
    query = MenuItem.query
    if q:
        query = query.filter(MenuItem.name.ilike(f"%{q}%"))
    if cat:
        query = query.filter(MenuItem.category_id == sanitize_int(cat))
    if avail:
        query = query.filter(MenuItem.availability == avail)
    items = query.order_by(MenuItem.display_order).all()
    categories = Category.query.all()
    return render_template("admin/menu.html", items=items, categories=categories)


@bp.route("/menu/add", methods=["GET", "POST"])
def menu_add():
    categories = Category.query.all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Food name is required.", "danger")
            return render_template("admin/menu_form.html", item=None, categories=categories)
        image = None
        if request.files.get("image"):
            image = save_uploaded_file(request.files["image"], "products")
        item = MenuItem(
            name=name, slug=name.lower().replace(" ", "-"),
            category_id=sanitize_int(request.form.get("category_id")),
            description=request.form.get("description", ""),
            ingredients=request.form.get("ingredients", ""),
            image=image or "uploads/products/default.png",
            price=sanitize_float(request.form.get("price")),
            discount=sanitize_float(request.form.get("discount", 0)),
            preparation_time=sanitize_int(request.form.get("preparation_time", 15)),
            availability=request.form.get("availability", "available"),
            featured=bool(request.form.get("featured")),
            display_order=sanitize_int(request.form.get("display_order", 0)),
            status=request.form.get("status", "active"),
        )
        db.session.add(item)
        db.session.commit()
        log_activity(current_user, "menu_item_added", "menu", request.remote_addr)
        flash("Menu item added.", "success")
        return redirect(url_for("admin.menu"))
    return render_template("admin/menu_form.html", item=None, categories=categories)


@bp.route("/menu/<int:mid>/edit", methods=["GET", "POST"])
def menu_edit(mid):
    item = MenuItem.query.get_or_404(mid)
    categories = Category.query.all()
    if request.method == "POST":
        item.name = request.form.get("name", "").strip()
        item.category_id = sanitize_int(request.form.get("category_id"))
        item.description = request.form.get("description", "")
        item.ingredients = request.form.get("ingredients", "")
        item.price = sanitize_float(request.form.get("price"))
        item.discount = sanitize_float(request.form.get("discount", 0))
        item.preparation_time = sanitize_int(request.form.get("preparation_time", 15))
        item.availability = request.form.get("availability", "available")
        item.featured = bool(request.form.get("featured"))
        item.display_order = sanitize_int(request.form.get("display_order", 0))
        item.status = request.form.get("status", "active")
        if request.files.get("image"):
            path = save_uploaded_file(request.files["image"], "products")
            if path:
                item.image = path
        db.session.commit()
        log_activity(current_user, "menu_item_updated", "menu", request.remote_addr)
        flash("Menu item updated.", "success")
        return redirect(url_for("admin.menu"))
    return render_template("admin/menu_form.html", item=item, categories=categories)


@bp.route("/menu/<int:mid>/delete", methods=["POST"])
def menu_delete(mid):
    item = MenuItem.query.get_or_404(mid)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})

# ===========================================================================
# ORDERS
# ===========================================================================
@bp.route("/orders")
def orders():
    status = request.args.get("status", "")
    q = request.args.get("q", "")
    query = Order.query
    if status:
        query = query.filter(Order.order_status == status)
    if q:
        query = query.filter(Order.order_number.ilike(f"%{q}%"))
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@bp.route("/orders/<int:oid>")
def order_detail(oid):
    order = Order.query.get_or_404(oid)
    return render_template("admin/order_detail.html", order=order)


@bp.route("/orders/<int:oid>/status", methods=["POST"])
def order_status_update(oid):
    order = Order.query.get_or_404(oid)
    new_status = request.form.get("status")
    order.order_status = new_status
    if new_status == "cancelled" and order.table:
        order.table.status = "available"
        order.table.current_order_id = None
    db.session.commit()
    log_activity(current_user, "order_status_changed", "orders", request.remote_addr)
    return jsonify({"ok": True})


# ===========================================================================
# TABLES
# ===========================================================================
@bp.route("/tables")
def tables():
    tables = RestaurantTable.query.order_by(RestaurantTable.table_number).all()
    return render_template("admin/tables.html", tables=tables)


@bp.route("/tables/add", methods=["GET", "POST"])
def table_add():
    if request.method == "POST":
        number = request.form.get("table_number", "").strip()
        if not number:
            flash("Table number is required.", "danger")
            return render_template("admin/table_form.html", table=None)
        t = RestaurantTable(
            table_number=number,
            capacity=sanitize_int(request.form.get("capacity", 2)),
            status=request.form.get("status", "available"),
            location=request.form.get("location", "indoor"),
        )
        db.session.add(t)
        db.session.commit()
        log_activity(current_user, "table_added", "tables", request.remote_addr)
        flash("Table added.", "success")
        return redirect(url_for("admin.tables"))
    return render_template("admin/table_form.html", table=None)


@bp.route("/tables/<int:tid>/edit", methods=["GET", "POST"])
def table_edit(tid):
    t = RestaurantTable.query.get_or_404(tid)
    if request.method == "POST":
        t.table_number = request.form.get("table_number", "").strip()
        t.capacity = sanitize_int(request.form.get("capacity", 2))
        t.status = request.form.get("status", "available")
        t.location = request.form.get("location", "indoor")
        db.session.commit()
        log_activity(current_user, "table_updated", "tables", request.remote_addr)
        flash("Table updated.", "success")
        return redirect(url_for("admin.tables"))
    return render_template("admin/table_form.html", table=t)


@bp.route("/tables/<int:tid>/delete", methods=["POST"])
def table_delete(tid):
    t = RestaurantTable.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# RESERVATIONS
# ===========================================================================
@bp.route("/reservations")
def reservations():
    status = request.args.get("status", "")
    query = Reservation.query
    if status:
        query = query.filter(Reservation.status == status)
    reservations = query.order_by(Reservation.reservation_date.desc()).all()
    tables = RestaurantTable.query.all()
    return render_template("admin/reservations.html", reservations=reservations, tables=tables)


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
    log_activity(current_user, "reservation_updated", "reservations", request.remote_addr)
    return jsonify({"ok": True})


@bp.route("/reservations/<int:rid>/assign", methods=["POST"])
def reservation_assign(rid):
    r = Reservation.query.get_or_404(rid)
    r.table_id = sanitize_int(request.form.get("table_id"))
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# BILLING & INVOICES
# ===========================================================================
@bp.route("/billing")
def billing():
    orders = Order.query.filter(Order.payment_status != "pending").order_by(Order.created_at.desc()).all()
    return render_template("admin/billing.html", orders=orders)


@bp.route("/orders/<int:oid>/invoice")
def view_invoice(oid):
    order = Order.query.get_or_404(oid)
    return render_template("admin/invoice.html", order=order)


@bp.route("/orders/<int:oid>/pay", methods=["GET", "POST"])
def pay_order(oid):
    order = Order.query.get_or_404(oid)
    if request.method == "POST":
        method = request.form.get("method", "cash")
        amount = sanitize_float(request.form.get("amount"), order.total)
        order.payment_method = method
        order.payment_status = "paid"
        pay = Payment(order_id=order.id, amount=amount, method=method,
                      status="paid", created_by=current_user.id)
        db.session.add(pay)
        # create invoice if not exists
        if not order.invoice:
            inv = Invoice(
                invoice_number=generate_invoice_number(), order_id=order.id,
                subtotal=order.subtotal, discount=order.discount, tax=order.tax,
                delivery_charges=order.delivery_charges, total=order.total,
            )
            db.session.add(inv)
        db.session.commit()
        log_activity(current_user, "payment_received", "payments", request.remote_addr)
        notify_role("ADMIN", "Payment Received", f"Payment for {order.order_number} received.", "success")
        flash("Payment recorded.", "success")
        return redirect(url_for("admin.billing"))
    return render_template("admin/pay_order.html", order=order)


# ===========================================================================
# PAYMENTS
# ===========================================================================
@bp.route("/payments")
def payments():
    pays = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template("admin/payments.html", payments=pays)

# ===========================================================================
# INVENTORY
# ===========================================================================
@bp.route("/inventory")
def inventory():
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    query = InventoryItem.query
    if q:
        query = query.filter(InventoryItem.name.ilike(f"%{q}%"))
    if status:
        query = query.filter(InventoryItem.status == status)
    items = query.order_by(InventoryItem.name).all()
    return render_template("admin/inventory.html", items=items)


@bp.route("/inventory/add", methods=["GET", "POST"])
def inventory_add():
    suppliers = Supplier.query.all()
    if request.method == "POST":
        item = InventoryItem(
            name=request.form.get("name", "").strip(),
            category=request.form.get("category", "general"),
            quantity=sanitize_float(request.form.get("quantity", 0)),
            unit=request.form.get("unit", "pcs"),
            minimum_stock=sanitize_float(request.form.get("minimum_stock", 10)),
            purchase_price=sanitize_float(request.form.get("purchase_price", 0)),
            supplier_id=sanitize_int(request.form.get("supplier_id")) or None,
            expiry_date=_parse_date(request.form.get("expiry_date")),
        )
        item.update_status()
        db.session.add(item)
        db.session.commit()
        if item.quantity > 0:
            db.session.add(InventoryTransaction(item_id=item.id, transaction_type="stock_in",
                                                quantity=item.quantity, reference="Initial"))
            db.session.commit()
        log_activity(current_user, "inventory_added", "inventory", request.remote_addr)
        flash("Inventory item added.", "success")
        return redirect(url_for("admin.inventory"))
    return render_template("admin/inventory_form.html", item=None, suppliers=suppliers)


@bp.route("/inventory/<int:iid>/edit", methods=["GET", "POST"])
def inventory_edit(iid):
    item = InventoryItem.query.get_or_404(iid)
    suppliers = Supplier.query.all()
    if request.method == "POST":
        item.name = request.form.get("name", "").strip()
        item.category = request.form.get("category", "general")
        item.quantity = sanitize_float(request.form.get("quantity", 0))
        item.unit = request.form.get("unit", "pcs")
        item.minimum_stock = sanitize_float(request.form.get("minimum_stock", 10))
        item.purchase_price = sanitize_float(request.form.get("purchase_price", 0))
        item.supplier_id = sanitize_int(request.form.get("supplier_id")) or None
        item.expiry_date = _parse_date(request.form.get("expiry_date"))
        item.update_status()
        db.session.commit()
        log_activity(current_user, "inventory_updated", "inventory", request.remote_addr)
        flash("Inventory item updated.", "success")
        return redirect(url_for("admin.inventory"))
    return render_template("admin/inventory_form.html", item=item, suppliers=suppliers)


@bp.route("/inventory/<int:iid>/stock", methods=["POST"])
def inventory_stock(iid):
    item = InventoryItem.query.get_or_404(iid)
    ttype = request.form.get("type")
    qty = sanitize_float(request.form.get("quantity", 0))
    if ttype == "stock_in":
        item.quantity += qty
    else:
        item.quantity = max(0, item.quantity - qty)
    item.update_status()
    db.session.add(InventoryTransaction(item_id=item.id, transaction_type=ttype,
                                        quantity=qty, reference=request.form.get("reference", ""),
                                        created_by=current_user.id))
    db.session.commit()
    if item.status in ("low_stock", "out_of_stock"):
        notify_role("ADMIN", "Low Stock Alert", f"{item.name} is {item.status.replace('_', ' ')}.", "warning")
    return jsonify({"ok": True, "status": item.status})


@bp.route("/inventory/<int:iid>/delete", methods=["POST"])
def inventory_delete(iid):
    item = InventoryItem.query.get_or_404(iid)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# SUPPLIERS
# ===========================================================================
@bp.route("/suppliers")
def suppliers():
    q = request.args.get("q", "")
    query = Supplier.query
    if q:
        query = query.filter(db.or_(Supplier.name.ilike(f"%{q}%"), Supplier.company.ilike(f"%{q}%")))
    suppliers = query.order_by(Supplier.name).all()
    return render_template("admin/suppliers.html", suppliers=suppliers)


@bp.route("/suppliers/add", methods=["GET", "POST"])
def supplier_add():
    if request.method == "POST":
        s = Supplier(
            name=request.form.get("name", "").strip(),
            company=request.form.get("company", ""),
            phone=request.form.get("phone", ""),
            email=request.form.get("email", ""),
            address=request.form.get("address", ""),
            products=request.form.get("products", ""),
            payment_status=request.form.get("payment_status", "paid"),
            status=request.form.get("status", "active"),
        )
        db.session.add(s)
        db.session.commit()
        flash("Supplier added.", "success")
        return redirect(url_for("admin.suppliers"))
    return render_template("admin/supplier_form.html", supplier=None)


@bp.route("/suppliers/<int:sid>/edit", methods=["GET", "POST"])
def supplier_edit(sid):
    s = Supplier.query.get_or_404(sid)
    if request.method == "POST":
        s.name = request.form.get("name", "").strip()
        s.company = request.form.get("company", "")
        s.phone = request.form.get("phone", "")
        s.email = request.form.get("email", "")
        s.address = request.form.get("address", "")
        s.products = request.form.get("products", "")
        s.payment_status = request.form.get("payment_status", "paid")
        s.status = request.form.get("status", "active")
        db.session.commit()
        flash("Supplier updated.", "success")
        return redirect(url_for("admin.suppliers"))
    return render_template("admin/supplier_form.html", supplier=s)


@bp.route("/suppliers/<int:sid>/delete", methods=["POST"])
def supplier_delete(sid):
    s = Supplier.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# PURCHASES
# ===========================================================================
@bp.route("/purchases")
def purchases():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template("admin/purchases.html", purchases=purchases)


@bp.route("/purchases/add", methods=["GET", "POST"])
def purchase_add():
    suppliers = Supplier.query.all()
    items = InventoryItem.query.all()
    if request.method == "POST":
        supplier_id = sanitize_int(request.form.get("supplier_id"))
        purchase = Purchase(
            purchase_number=generate_purchase_number(),
            supplier_id=supplier_id,
            purchase_date=_parse_date(request.form.get("purchase_date")) or date.today(),
            payment_status=request.form.get("payment_status", "pending"),
            note=request.form.get("note", ""),
            created_by=current_user.id,
        )
        db.session.add(purchase)
        db.session.flush()
        item_ids = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")
        prices = request.form.getlist("unit_price")
        total = 0.0
        for iid, qty, price in zip(item_ids, quantities, prices):
            q = sanitize_float(qty)
            p = sanitize_float(price)
            if not iid or q <= 0:
                continue
            line = q * p
            total += line
            pi = PurchaseItem(purchase_id=purchase.id, inventory_item_id=sanitize_int(iid),
                              quantity=q, unit_price=p, total=line)
            db.session.add(pi)
            inv = InventoryItem.query.get(sanitize_int(iid))
            if inv:
                inv.quantity += q
                inv.update_status()
                db.session.add(InventoryTransaction(item_id=inv.id, transaction_type="stock_in",
                                                    quantity=q, reference=purchase.purchase_number))
        purchase.total = total
        db.session.commit()
        log_activity(current_user, "purchase_completed", "purchases", request.remote_addr)
        flash("Purchase recorded. Inventory updated.", "success")
        return redirect(url_for("admin.purchases"))
    return render_template("admin/purchase_form.html", suppliers=suppliers, items=items)


@bp.route("/purchases/<int:pid>/delete", methods=["POST"])
def purchase_delete(pid):
    p = Purchase.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# DELIVERY
# ===========================================================================
@bp.route("/delivery")
def delivery():
    deliveries = Delivery.query.order_by(Delivery.created_at.desc()).all()
    staff = Staff.query.join(User).filter(User.role.has(Role.name == "WAITER")).all()
    return render_template("admin/delivery.html", deliveries=deliveries, staff=staff)


@bp.route("/delivery/<int:did>/status", methods=["POST"])
def delivery_status(did):
    d = Delivery.query.get_or_404(did)
    d.status = request.form.get("status", d.status)
    if d.status == "delivered":
        d.delivered_at = datetime.utcnow()
        d.order.order_status = "completed"
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/delivery/<int:did>/assign", methods=["POST"])
def delivery_assign(did):
    d = Delivery.query.get_or_404(did)
    d.delivery_staff_id = sanitize_int(request.form.get("staff_id")) or None
    d.status = "out_for_delivery"
    d.assigned_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# OFFERS
# ===========================================================================
@bp.route("/offers")
def offers():
    offers = Offer.query.order_by(Offer.display_order).all()
    return render_template("admin/offers.html", offers=offers)


@bp.route("/offers/add", methods=["GET", "POST"])
def offer_add():
    if request.method == "POST":
        image = None
        if request.files.get("image"):
            image = save_uploaded_file(request.files["image"], "offers")
        o = Offer(
            name=request.form.get("name", "").strip(),
            description=request.form.get("description", ""),
            image=image, discount_type=request.form.get("discount_type", "percentage"),
            discount_value=sanitize_float(request.form.get("discount_value", 0)),
            start_date=_parse_date(request.form.get("start_date")),
            end_date=_parse_date(request.form.get("end_date")),
            status=request.form.get("status", "active"),
            display_order=sanitize_int(request.form.get("display_order", 0)),
        )
        db.session.add(o)
        db.session.commit()
        flash("Offer added.", "success")
        return redirect(url_for("admin.offers"))
    return render_template("admin/offer_form.html", offer=None)


@bp.route("/offers/<int:oid>/edit", methods=["GET", "POST"])
def offer_edit(oid):
    o = Offer.query.get_or_404(oid)
    if request.method == "POST":
        o.name = request.form.get("name", "").strip()
        o.description = request.form.get("description", "")
        o.discount_type = request.form.get("discount_type", "percentage")
        o.discount_value = sanitize_float(request.form.get("discount_value", 0))
        o.start_date = _parse_date(request.form.get("start_date"))
        o.end_date = _parse_date(request.form.get("end_date"))
        o.status = request.form.get("status", "active")
        o.display_order = sanitize_int(request.form.get("display_order", 0))
        if request.files.get("image"):
            path = save_uploaded_file(request.files["image"], "offers")
            if path:
                o.image = path
        db.session.commit()
        flash("Offer updated.", "success")
        return redirect(url_for("admin.offers"))
    return render_template("admin/offer_form.html", offer=o)


@bp.route("/offers/<int:oid>/delete", methods=["POST"])
def offer_delete(oid):
    o = Offer.query.get_or_404(oid)
    db.session.delete(o)
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# REVIEWS
# ===========================================================================
@bp.route("/reviews")
def reviews():
    status = request.args.get("status", "")
    query = Review.query
    if status:
        query = query.filter(Review.status == status)
    reviews = query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=reviews)


@bp.route("/reviews/<int:rid>/status", methods=["POST"])
def review_status(rid):
    r = Review.query.get_or_404(rid)
    action = request.form.get("action")
    if action == "approve":
        r.status = "approved"
    elif action == "reject":
        r.status = "rejected"
    elif action == "delete":
        db.session.delete(r)
        db.session.commit()
        return jsonify({"ok": True})
    db.session.commit()
    return jsonify({"ok": True})


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None

# ===========================================================================
# REPORTS
# ===========================================================================
@bp.route("/reports")
def reports():
    range_type = request.args.get("range", "this_month")
    start, end = _date_range(range_type)
    orders = Order.query.filter(Order.created_at.between(start, end)).all()
    paid = [o for o in orders if o.payment_status == "paid"]
    revenue = sum(o.total for o in paid)
    expenses = sum(p.total for p in Purchase.query.filter(Purchase.created_at.between(start, end)).all())
    profit = revenue - expenses
    order_count = len(orders)
    avg_order = round(revenue / order_count, 2) if order_count else 0

    # Sales by day
    sales_by_day = {}
    for o in paid:
        key = o.created_at.strftime("%Y-%m-%d")
        sales_by_day[key] = sales_by_day.get(key, 0) + o.total
    chart_labels = sorted(sales_by_day.keys())
    chart_values = [round(sales_by_day[k], 2) for k in chart_labels]

    # Popular food
    popular = (
        db.session.query(MenuItem.name, db.func.sum(OrderItem.quantity).label("qty"))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at.between(start, end))
        .group_by(MenuItem.name).order_by(db.func.sum(OrderItem.quantity).desc())
        .limit(10).all()
    )
    popular_food = [{"name": p[0], "qty": int(p[1] or 0)} for p in popular]

    return render_template("admin/reports.html",
        range_type=range_type, revenue=revenue, expenses=expenses, profit=profit,
        order_count=order_count, avg_order=avg_order,
        chart_labels=chart_labels, chart_values=chart_values, popular_food=popular_food,
        start=start, end=end)


# ===========================================================================
# ANALYTICS
# ===========================================================================
@bp.route("/analytics")
def analytics():
    # Monthly revenue for last 12 months
    months = []
    values = []
    from dateutil.relativedelta import relativedelta
    now = datetime.utcnow()
    for i in range(11, -1, -1):
        m = now - relativedelta(months=i)
        months.append(m.strftime("%b %Y"))
        start = m.replace(day=1, hour=0, minute=0, second=0)
        if i == 0:
            end = now
        else:
            end = (m + relativedelta(months=1)).replace(day=1) - timedelta(days=1)
            end = end.replace(hour=23, minute=59, second=59)
        rev = sum(o.total for o in Order.query.filter(Order.created_at.between(start, end)).all()
                  if o.payment_status == "paid")
        values.append(round(rev, 2))

    # Order status distribution
    status_dist = (
        db.session.query(Order.order_status, db.func.count(Order.id))
        .group_by(Order.order_status).all()
    )
    status_labels = [s[0].replace("_", " ").title() for s in status_dist]
    status_values = [s[1] for s in status_dist]

    # Table occupancy
    total_tables = RestaurantTable.query.count()
    occupied = RestaurantTable.query.filter_by(status="occupied").count()
    available = RestaurantTable.query.filter_by(status="available").count()
    reserved = RestaurantTable.query.filter_by(status="reserved").count()
    oos = RestaurantTable.query.filter_by(status="out_of_service").count()

    # Inventory usage (top items by quantity)
    inv = InventoryItem.query.order_by(InventoryItem.quantity.desc()).limit(8).all()
    inv_labels = [i.name for i in inv]
    inv_values = [round(i.quantity, 1) for i in inv]

    return render_template("admin/analytics.html",
        months=months, values=values, status_labels=status_labels, status_values=status_values,
        total_tables=total_tables, occupied=occupied, available=available,
        reserved=reserved, oos=oos, inv_labels=inv_labels, inv_values=inv_values)


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================
@bp.route("/notifications")
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("admin/notifications.html", notifications=notes)


@bp.route("/notifications/<int:nid>/read", methods=["POST"])
def notification_read(nid):
    n = Notification.query.get_or_404(nid)
    n.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


# ===========================================================================
# ACTIVITY LOGS
# ===========================================================================
@bp.route("/activity-logs")
def activity_logs():
    q = request.args.get("q", "")
    module = request.args.get("module", "")
    query = ActivityLog.query
    if q:
        query = query.filter(db.or_(ActivityLog.username.ilike(f"%{q}%"), ActivityLog.action.ilike(f"%{q}%")))
    if module:
        query = query.filter(ActivityLog.module == module)
    logs = query.order_by(ActivityLog.created_at.desc()).limit(500).all()
    modules = db.session.query(ActivityLog.module).distinct().all()
    modules = [m[0] for m in modules]
    return render_template("admin/activity_logs.html", logs=logs, modules=modules)


def _date_range(range_type):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if range_type == "today":
        return today, today + timedelta(days=1)
    if range_type == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)
    if range_type == "this_month":
        start = today.replace(day=1)
        return start, (start + relativedelta(months=1)) - timedelta(days=1) + timedelta(hours=23, minutes=59)
    if range_type == "this_year":
        start = today.replace(month=1, day=1)
        return start, today + timedelta(days=1)
    # custom
    start_s = request.args.get("start")
    end_s = request.args.get("end")
    start = _parse_date(start_s) or today.replace(day=1)
    end = _parse_date(end_s) or today
    end = datetime.combine(end, datetime.max.time())
    return datetime.combine(start, datetime.min.time()), end
