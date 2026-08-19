"""Orders, order items, kitchen orders, payments, invoices and delivery."""
from datetime import datetime
from extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    order_type = db.Column(db.String(20), default="dine_in")  # dine_in | takeaway | delivery
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"))
    waiter_id = db.Column(db.Integer, db.ForeignKey("staff.id"))
    chef_id = db.Column(db.Integer, db.ForeignKey("staff.id"))

    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    delivery_charges = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)

    order_status = db.Column(db.String(20), default="new")  # new | accepted | preparing | ready | served | completed | cancelled
    payment_status = db.Column(db.String(20), default="pending")  # pending | paid | partially_paid | refunded
    payment_method = db.Column(db.String(20), default="cash")
    special_instructions = db.Column(db.Text)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    kitchen = db.relationship("KitchenOrder", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    invoice = db.relationship("Invoice", backref="order", uselist=False, cascade="all, delete-orphan")
    delivery_record = db.relationship("Delivery", backref="order", uselist=False, cascade="all, delete-orphan")

    customer = db.relationship("Customer", backref="orders")
    table = db.relationship("RestaurantTable", backref="orders", foreign_keys=[table_id])
    waiter = db.relationship("Staff", foreign_keys=[waiter_id], backref="waiter_orders")
    chef = db.relationship("Staff", foreign_keys=[chef_id], backref="chef_orders")

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    special_instructions = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending | preparing | ready | served

    @property
    def line_total(self):
        price = self.unit_price or 0
        disc = self.discount or 0
        return round((price - (price * disc / 100.0)) * self.quantity, 2)

    def __repr__(self):
        return f"<OrderItem {self.id}>"


class KitchenOrder(db.Model):
    """Kitchen display system tracking per order."""

    __tablename__ = "kitchen_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    status = db.Column(db.String(20), default="new")  # new | accepted | preparing | ready
    accepted_by = db.Column(db.Integer, db.ForeignKey("staff.id"))
    accepted_at = db.Column(db.DateTime)
    preparing_at = db.Column(db.DateTime)
    ready_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    accepted_by_staff = db.relationship("Staff", backref="accepted_kitchen_orders")

    def __repr__(self):
        return f"<KitchenOrder {self.order_id} {self.status}>"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), default="cash")  # cash | card | bank_transfer | online
    status = db.Column(db.String(20), default="paid")  # pending | paid | partially_paid | refunded
    reference = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __repr__(self):
        return f"<Payment {self.id} {self.amount}>"


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    delivery_charges = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


class Delivery(db.Model):
    __tablename__ = "delivery"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    delivery_staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"))
    address = db.Column(db.Text)
    phone = db.Column(db.String(30))
    delivery_charges = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="confirmed")  # confirmed | preparing | out_for_delivery | delivered | cancelled
    assigned_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    delivery_staff = db.relationship("Staff", backref="deliveries")

    def __repr__(self):
        return f"<Delivery {self.id}>"
