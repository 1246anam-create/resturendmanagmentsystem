"""Restaurant tables and reservations."""
from datetime import datetime, date, time
from extensions import db


class RestaurantTable(db.Model):
    __tablename__ = "tables"

    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    status = db.Column(db.String(20), default="available")  # available | occupied | reserved | out_of_service
    location = db.Column(db.String(50))  # indoor | outdoor | vip
    current_order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    assigned_waiter_id = db.Column(db.Integer, db.ForeignKey("staff.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_waiter = db.relationship("Staff", backref="assigned_tables")

    def __repr__(self):
        return f"<Table {self.table_number}>"


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    customer_name = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    reservation_date = db.Column(db.Date, nullable=False)
    reservation_time = db.Column(db.Time, default=time(19, 0))
    guests = db.Column(db.Integer, default=2)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"))
    special_request = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending | confirmed | completed | cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("Customer", backref="reservations")
    table = db.relationship("RestaurantTable", backref="reservations")

    def __repr__(self):
        return f"<Reservation {self.id}>"
