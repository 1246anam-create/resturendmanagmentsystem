"""Authentication helpers and role-based access control decorators."""
from functools import wraps
from flask import abort, redirect, url_for, request
from flask_login import current_user
from extensions import db
from models.user import Role, Permission, role_permissions


# Canonical permission catalogue. These names are referenced across the app.
PERMISSIONS = [
    # Admin / system
    ("dashboard_view", "View Dashboard"),
    ("staff_manage", "Manage Staff"),
    ("roles_manage", "Manage Roles & Permissions"),
    ("customers_manage", "Manage Customers"),
    ("menu_manage", "Manage Menu"),
    ("categories_manage", "Manage Categories"),
    ("orders_manage", "Manage Orders"),
    ("kitchen_manage", "Manage Kitchen"),
    ("tables_manage", "Manage Tables"),
    ("reservations_manage", "Manage Reservations"),
    ("billing_manage", "Manage Billing"),
    ("payments_manage", "Manage Payments"),
    ("inventory_manage", "Manage Inventory"),
    ("suppliers_manage", "Manage Suppliers"),
    ("purchases_manage", "Manage Purchases"),
    ("delivery_manage", "Manage Delivery"),
    ("offers_manage", "Manage Offers"),
    ("reviews_manage", "Manage Reviews"),
    ("reports_view", "View Reports"),
    ("analytics_view", "View Analytics"),
    ("cms_manage", "Manage Website CMS"),
    ("header_manage", "Manage Header"),
    ("footer_manage", "Manage Footer"),
    ("banners_manage", "Manage Banners"),
    ("services_manage", "Manage Services"),
    ("about_manage", "Manage About Us"),
    ("theme_manage", "Manage Theme"),
    ("branding_manage", "Manage Branding"),
    ("settings_manage", "Manage Settings"),
    ("notifications_view", "View Notifications"),
    ("activity_logs_view", "View Activity Logs"),
    # Role-specific operational
    ("waiter_orders", "Waiter Order Operations"),
    ("chef_kitchen", "Chef Kitchen Operations"),
    ("manager_operations", "Manager Operations"),
    ("customer_portal", "Customer Portal Access"),
]


def create_default_roles_and_permissions():
    """Idempotently create the permission catalogue and the five system roles."""
    from models.user import Permission, Role

    # Permissions
    perm_map = {}
    for name, desc in PERMISSIONS:
        perm = Permission.query.filter_by(name=name).first()
        if not perm:
            perm = Permission(name=name, description=desc)
            db.session.add(perm)
            db.session.flush()
        perm_map[name] = perm

    def get_or_create_role(name, display, desc, perms):
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, display_name=display, description=desc, is_system=True)
            db.session.add(role)
            db.session.flush()
        for p in perms:
            role.add_permission(perm_map[p])
        return role

    # ADMIN: everything
    admin_perms = [p[0] for p in PERMISSIONS]
    get_or_create_role("ADMIN", "Administrator", "Full system access", admin_perms)

    # MANAGER
    manager_perms = [
        "dashboard_view", "orders_manage", "tables_manage", "reservations_manage",
        "customers_manage", "inventory_manage", "suppliers_manage", "purchases_manage",
        "reports_view", "analytics_view", "manager_operations", "notifications_view",
    ]
    get_or_create_role("MANAGER", "Manager", "Restaurant operations", manager_perms)

    # WAITER
    waiter_perms = [
        "dashboard_view", "orders_manage", "tables_manage", "reservations_manage",
        "customers_manage", "waiter_orders", "notifications_view",
    ]
    get_or_create_role("WAITER", "Waiter", "Tables, customers and orders", waiter_perms)

    # CHEF
    chef_perms = [
        "dashboard_view", "kitchen_manage", "chef_kitchen", "notifications_view",
    ]
    get_or_create_role("CHEF", "Chef", "Kitchen and food preparation", chef_perms)

    # CUSTOMER
    customer_perms = ["customer_portal"]
    get_or_create_role("CUSTOMER", "Customer", "Website customer", customer_perms)

    db.session.commit()


def permission_required(perm_name):
    """Decorator: require a specific permission for the current user."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.endpoint))
            if not current_user.has_permission(perm_name):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    """Decorator: require the current user to have one of the given role names."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.endpoint))
            if current_user.role is None or current_user.role.name not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
