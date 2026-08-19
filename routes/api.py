"""JSON API endpoints used by dashboards (kitchen display, order actions, etc.)."""
import json
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models.order import Order, OrderItem, KitchenOrder
from models.table import RestaurantTable
from models.settings import Notification
from models.user import Staff
from utils.auth import permission_required, role_required
from utils.helpers import log_activity, notify_role, notify
from datetime import datetime

bp = Blueprint("api", __name__)


@bp.route("/kitchen/orders")
@login_required
def kitchen_orders():
    """Return kitchen orders grouped by status for the KDS."""
    statuses = ["new", "accepted", "preparing", "ready"]
    result = {s: [] for s in statuses}
    orders = (
        Order.query.filter(Order.order_status.in_(["new", "accepted", "preparing", "ready"]))
        .order_by(Order.created_at.asc())
        .all()
    )
    for o in orders:
        ko = o.kitchen.first()
        status = ko.status if ko else "new"
        result[status].append(_serialize_kitchen_order(o, ko))
    return jsonify(result)


def _serialize_kitchen_order(o, ko):
    return {
        "id": o.id,
        "order_number": o.order_number,
        "table": o.table.table_number if o.table else "Takeaway" if o.order_type == "takeaway" else "Delivery",
        "waiter": o.waiter.full_name if o.waiter else "-",
        "order_time": o.created_at.strftime("%H:%M"),
        "type": o.order_type,
        "status": ko.status if ko else "new",
        "items": [
            {
                "name": it.menu_item.name if it.menu_item else "Item",
                "qty": it.quantity,
                "instructions": it.special_instructions or "",
                "status": it.status,
            }
            for it in o.items
        ],
    }


@bp.route("/kitchen/<int:order_id>/<action>", methods=["POST"])
@login_required
@role_required("CHEF", "ADMIN", "MANAGER")
def kitchen_action(order_id, action):
    """Accept / start-preparing / mark-ready for a kitchen order."""
    order = Order.query.get_or_404(order_id)
    ko = order.kitchen.first()
    if not ko:
        ko = KitchenOrder(order_id=order.id, status="new")
        db.session.add(ko)
    now = datetime.utcnow()
    if action == "accept":
        ko.status = "accepted"
        ko.accepted_by = current_user.id if current_user.staff_profile else None
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
        return jsonify({"ok": False, "error": "invalid action"}), 400
    db.session.commit()
    log_activity(current_user, f"kitchen_{action}", "kitchen", request.remote_addr)
    return jsonify({"ok": True, "status": ko.status})


@bp.route("/waiter/order/<int:order_id>/serve", methods=["POST"])
@login_required
@role_required("WAITER", "ADMIN", "MANAGER")
def mark_served(order_id):
    order = Order.query.get_or_404(order_id)
    order.order_status = "served"
    for it in order.items:
        it.status = "served"
    ko = order.kitchen.first()
    if ko:
        ko.status = "ready"
    db.session.commit()
    log_activity(current_user, "order_served", "orders", request.remote_addr)
    return jsonify({"ok": True})


@bp.route("/waiter/order/<int:order_id>/complete", methods=["POST"])
@login_required
@role_required("WAITER", "ADMIN", "MANAGER")
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.order_status = "completed"
    if order.table:
        order.table.status = "available"
        order.table.current_order_id = None
    db.session.commit()
    log_activity(current_user, "order_completed", "orders", request.remote_addr)
    return jsonify({"ok": True})


@bp.route("/notifications")
@login_required
def notifications():
    notes = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        "unread": unread,
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "link": n.link,
                "is_read": n.is_read,
                "time": n.created_at.strftime("%b %d, %H:%M"),
            }
            for n in notes
        ],
    })


@bp.route("/notifications/mark-read", methods=["POST"])
@login_required
def mark_read():
    data = request.get_json(silent=True) or {}
    nid = data.get("id")
    q = Notification.query.filter_by(user_id=current_user.id)
    if nid:
        q = q.filter_by(id=nid)
    q.update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/tables/status")
@login_required
def tables_status():
    tables = RestaurantTable.query.all()
    return jsonify([
        {
            "id": t.id,
            "number": t.table_number,
            "status": t.status,
            "capacity": t.capacity,
            "order": (t.orders[0].order_number if t.orders else None),
        }
        for t in tables
    ])
