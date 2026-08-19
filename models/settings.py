"""CMS & settings models: services, banners, about, header, footer, restaurant,
theme, notifications, activity logs and offers."""
from datetime import datetime, date
from extensions import db


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(60), default="utensils")  # font-awesome style name
    image = db.Column(db.String(255))
    button_text = db.Column(db.String(60), default="Learn More")
    button_link = db.Column(db.String(200), default="#")
    display_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Service {self.title}>"


class Banner(db.Model):
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255), default="uploads/banners/default.jpg")
    button_text = db.Column(db.String(60), default="Explore Menu")
    button_link = db.Column(db.String(200), default="/menu")
    secondary_button_text = db.Column(db.String(60))
    secondary_button_link = db.Column(db.String(200))
    display_order = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Banner {self.title}>"


class AboutContent(db.Model):
    __tablename__ = "about_content"

    id = db.Column(db.Integer, primary_key=True)
    story_title = db.Column(db.String(160), default="Our Story")
    story = db.Column(db.Text)
    mission_title = db.Column(db.String(160), default="Our Mission")
    mission = db.Column(db.Text)
    vision_title = db.Column(db.String(160), default="Our Vision")
    vision = db.Column(db.Text)
    history = db.Column(db.Text)
    chef_name = db.Column(db.String(120))
    chef_title = db.Column(db.String(120))
    chef_bio = db.Column(db.Text)
    chef_image = db.Column(db.String(255))
    image_1 = db.Column(db.String(255))
    image_2 = db.Column(db.String(255))
    image_3 = db.Column(db.String(255))
    stat1_label = db.Column(db.String(60), default="Years Experience")
    stat1_value = db.Column(db.String(30), default="15+")
    stat2_label = db.Column(db.String(60), default="Menu Items")
    stat2_value = db.Column(db.String(30), default="50+")
    stat3_label = db.Column(db.String(60), default="Happy Customers")
    stat3_value = db.Column(db.String(30), default="10K+")
    stat4_label = db.Column(db.String(60), default="Rating")
    stat4_value = db.Column(db.String(30), default="4.9/5")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AboutContent {self.id}>"


class HeaderSettings(db.Model):
    __tablename__ = "header_settings"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_name = db.Column(db.String(120), default="Restaurant")
    logo = db.Column(db.String(255), default="uploads/logo/logo.png")
    cta_text = db.Column(db.String(40), default="Book a Table")
    cta_link = db.Column(db.String(200), default="/reservation")
    contact_phone = db.Column(db.String(30))
    contact_email = db.Column(db.String(120))
    show_reservation_button = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<HeaderSettings {self.id}>"


class FooterSettings(db.Model):
    __tablename__ = "footer_settings"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    facebook = db.Column(db.String(200))
    instagram = db.Column(db.String(200))
    youtube = db.Column(db.String(200))
    twitter = db.Column(db.String(200))
    linkedin = db.Column(db.String(200))
    opening_hours = db.Column(db.Text, default="Mon-Sun: 9:00 AM - 11:00 PM")
    copyright_text = db.Column(db.String(200), default="All rights reserved.")
    privacy_policy_link = db.Column(db.String(200), default="/privacy")
    terms_link = db.Column(db.String(200), default="/terms")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FooterSettings {self.id}>"


class RestaurantSettings(db.Model):
    __tablename__ = "restaurant_settings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="Restaurant Management System")
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    currency = db.Column(db.String(10), default="USD")
    currency_symbol = db.Column(db.String(10), default="$")
    tax_rate = db.Column(db.Float, default=10.0)  # percent
    delivery_charges = db.Column(db.Float, default=5.0)
    opening_hours = db.Column(db.Text, default="Mon-Sun: 9:00 AM - 11:00 PM")
    status = db.Column(db.String(20), default="open")  # open | closed
    favicon = db.Column(db.String(255), default="uploads/favicon/favicon.ico")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RestaurantSettings {self.id}>"


class ThemeSettings(db.Model):
    __tablename__ = "theme_settings"

    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(20), default="#c8962a")
    secondary_color = db.Column(db.String(20), default="#1f1d1b")
    accent_color = db.Column(db.String(20), default="#e07b39")
    background_color = db.Column(db.String(20), default="#faf7f0")
    surface_color = db.Column(db.String(20), default="#ffffff")
    text_color = db.Column(db.String(20), default="#1f1d1b")
    muted_text_color = db.Column(db.String(20), default="#6b6b6b")
    button_color = db.Column(db.String(20), default="#c8962a")
    font_family = db.Column(db.String(60), default="'Poppins', sans-serif")
    border_radius = db.Column(db.String(10), default="12px")
    mode = db.Column(db.String(20), default="light")  # light | dark
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ThemeSettings {self.id}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text)
    type = db.Column(db.String(30), default="info")  # info | success | warning | danger
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    username = db.Column(db.String(80))
    action = db.Column(db.String(120), nullable=False)
    module = db.Column(db.String(60), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.module}.{self.action}>"


class Offer(db.Model):
    __tablename__ = "offers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    discount_type = db.Column(db.String(20), default="percentage")  # percentage | fixed
    discount_value = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="active")
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_active_now(self):
        today = date.today()
        if self.status != "active":
            return False
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    def __repr__(self):
        return f"<Offer {self.name}>"
