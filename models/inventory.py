"""Inventory, inventory transactions, suppliers and purchases."""
from datetime import datetime, date
from extensions import db


class InventoryItem(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), default="general")
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default="pcs")
    minimum_stock = db.Column(db.Float, default=10.0)
    purchase_price = db.Column(db.Float, default=0.0)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="in_stock")  # in_stock | low_stock | out_of_stock | expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = db.relationship("Supplier", backref="items")
    transactions = db.relationship("InventoryTransaction", backref="item", lazy="dynamic")

    def update_status(self):
        today = date.today()
        if self.expiry_date and self.expiry_date <= today:
            self.status = "expired"
        elif self.quantity <= 0:
            self.status = "out_of_stock"
        elif self.quantity <= self.minimum_stock:
            self.status = "low_stock"
        else:
            self.status = "in_stock"

    def __repr__(self):
        return f"<InventoryItem {self.name}>"


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # stock_in | stock_out
    quantity = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(120))  # order/purchase id
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __repr__(self):
        return f"<InventoryTransaction {self.id}>"


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    products = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default="paid")  # paid | pending | partial
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship("Purchase", backref="supplier", lazy="dynamic")

    def __repr__(self):
        return f"<Supplier {self.name}>"


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    purchase_number = db.Column(db.String(30), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    total = db.Column(db.Float, default=0.0)
    purchase_date = db.Column(db.Date, default=date.today)
    payment_status = db.Column(db.String(20), default="pending")  # pending | paid | partially_paid
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    items = db.relationship("PurchaseItem", backref="purchase", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Purchase {self.purchase_number}>"


class PurchaseItem(db.Model):
    __tablename__ = "purchase_items"

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id"), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey("inventory.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)

    inventory_item = db.relationship("InventoryItem", backref="purchase_items")

    def __repr__(self):
        return f"<PurchaseItem {self.id}>"
