"""Menu: categories, menu items and reviews."""
from datetime import datetime
from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="active")  # active | inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("MenuItem", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name}>"


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.Text)
    image = db.Column(db.String(255), default="uploads/products/default.png")
    price = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, default=0.0)  # percent
    preparation_time = db.Column(db.Integer, default=15)  # minutes
    availability = db.Column(db.String(20), default="available")  # available | unavailable
    featured = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    display_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", backref="menu_item", lazy="dynamic")

    @property
    def final_price(self):
        if self.discount and self.discount > 0:
            return round(self.price - (self.price * self.discount / 100.0), 2)
        return round(self.price, 2)

    def __repr__(self):
        return f"<MenuItem {self.name}>"


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending | approved | rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("Customer", backref="reviews")
    menu_item = db.relationship("MenuItem", backref="reviews")

    def __repr__(self):
        return f"<Review {self.id} {self.rating}*>"
