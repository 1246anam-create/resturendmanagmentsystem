"""User, Role, Permission, Staff and Customer models (auth + RBAC)."""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


# Association table: many-to-many between roles and permissions
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # ADMIN, MANAGER, WAITER, CHEF, CUSTOMER
    display_name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255))
    is_system = db.Column(db.Boolean, default=False)  # system roles cannot be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship(
        "Permission", secondary=role_permissions, backref="roles", lazy="dynamic"
    )
    users = db.relationship("User", backref="role", lazy="dynamic")

    def add_permission(self, perm):
        if not self.has_permission(perm.name):
            self.permissions.append(perm)

    def remove_permission(self, perm):
        if self.has_permission(perm.name):
            self.permissions.remove(perm)

    def has_permission(self, perm_name):
        return self.permissions.filter(Permission.name == perm_name).first() is not None

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<Permission {self.name}>"


class User(db.Model, UserMixin):
    """Base user account used for authentication across all roles."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    status = db.Column(db.String(20), default="active")  # active | inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    # Polymorphic link to profile (staff or customer)
    profile_type = db.Column(db.String(20))  # staff | customer
    profile_id = db.Column(db.Integer)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.status == "active"

    def has_permission(self, perm_name):
        return self.role and self.role.has_permission(perm_name)

    def __repr__(self):
        return f"<User {self.username}>"


class Staff(db.Model):
    """Staff profile (admin, manager, waiter, chef)."""

    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    profile_image = db.Column(db.String(255), default="uploads/staff/default.png")
    joining_date = db.Column(db.Date, default=date.today)
    emergency_contact = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("staff_profile", uselist=False))

    def __repr__(self):
        return f"<Staff {self.full_name}>"


class Customer(db.Model):
    """Customer profile for website users."""

    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    profile_image = db.Column(db.String(255), default="uploads/customers/default.png")
    date_of_birth = db.Column(db.Date)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("customer_profile", uselist=False))

    def __repr__(self):
        return f"<Customer {self.full_name}>"
