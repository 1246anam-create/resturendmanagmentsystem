"""Chef / Kitchen blueprint: Kitchen Display System."""
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models.order import Order, OrderItem, KitchenOrder
from utils.helpers import log_activity, notify_role
from datetime import datetime

bp = Blueprint("chef", __name__, url_prefix="/chef")


@bp.before_request
def require_chef():
    if not current_user.is_authenticated or current_user.role.name not in ("ADMIN", "MANAGER", "CHEF"):
        abort(403)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    statuses = ["new", "accepted", "preparing", "ready"]
    columns = {s: [] for s in statuses}
    orders = (
        Order.query.filter(Order.order_status.in_(statuses))
        .order_by(Order.created_at.asc()).all()
    )
    for o in orders:
        ko = o.kitchen.first()
        status = ko.status if ko else "new"
        columns[status].append(o)
    return render_template("chef/dashboard.html", columns=columns, statuses=statuses)


@bp.route("/orders/<int:oid>/<action>", methods=["POST"])
def order_action(oid, action):
    order = Order.query.get_or_404(oid)
    ko = order.kitchen.first()
    if not ko:
        ko = KitchenOrder(order_id=order.id, status="new")
        db.session.add(ko)
    now = datetime.utcnow()
    if action == "accept":
        ko.status = "accepted"
        ko.accepted_by = current_user.staff_profile.id if current_user.staff_profile else None
        ko.accepted_at = now
        order.order_status = "accepted"
        order.chef_id = current_user.staff_profile.id if current_user.staff_profile else None
    elif action == "prepare":
        ko.status = "preparing"
        ko.preparing_at = now
        order.order_status = "preparing"
        for it in order.items:
            it.status = "preparing"
    elif action == "ready":
        ko.status = "ready"
        ko.ready_at = now
        order.order_status = "ready"
        for it in order.items:
            it.status = "ready"
        notify_role("WAITER", "Order Ready", f"Order {order.order_number} is ready to serve.", "success", "/waiter/orders")
    else:
        return jsonify({"ok": False, "error": "invalid"}), 400
    db.session.commit()
    log_activity(current_user, f"kitchen_{action}", "kitchen", request.remote_addr)
    return jsonify({"ok": True, "status": ko.status})
