"""Seed script: creates default admin, sample data, and CMS defaults."""
from extensions import db
from models.user import User, Staff, Customer, Role, Permission
from models.menu import Category, MenuItem
from models.table import RestaurantTable, Reservation
from models.order import Order, OrderItem, KitchenOrder
from models.inventory import InventoryItem, Supplier
from models.settings import (
    Service, Banner, AboutContent, HeaderSettings, FooterSettings,
    RestaurantSettings, ThemeSettings, Offer,
)
from utils.auth import create_default_roles_and_permissions
from utils.helpers import generate_order_number
from datetime import date, datetime, time


def seed_all():
    create_default_roles_and_permissions()

    # ---- Default settings rows (singletons) ----
    if not RestaurantSettings.query.first():
        db.session.add(RestaurantSettings(
            name="Savory Bites Restaurant", phone="+1 234 567 8900",
            email="info@savorybites.com", address="123 Gourmet Avenue, Food City",
            currency="USD", currency_symbol="$", tax_rate=10.0, delivery_charges=5.0,
            opening_hours="Mon-Sun: 9:00 AM - 11:00 PM", status="open",
        ))
    if not HeaderSettings.query.first():
        db.session.add(HeaderSettings(
            restaurant_name="Savory Bites", cta_text="Book a Table",
            cta_link="/reservation", contact_phone="+1 234 567 8900",
            contact_email="info@savorybites.com", show_reservation_button=True,
        ))
    if not FooterSettings.query.first():
        db.session.add(FooterSettings(
            description="Savory Bites is a premium restaurant serving delicious meals crafted with passion and the finest ingredients.",
            facebook="https://facebook.com", instagram="https://instagram.com",
            youtube="https://youtube.com", opening_hours="Mon-Sun: 9:00 AM - 11:00 PM",
            copyright_text="© 2024 Savory Bites Restaurant. All rights reserved.",
        ))
    if not ThemeSettings.query.first():
        db.session.add(ThemeSettings())
    if not AboutContent.query.first():
        db.session.add(AboutContent(
            story_title="Our Story", story="Founded with a passion for exceptional food, Savory Bites brings together culinary tradition and modern creativity.",
            mission_title="Our Mission", mission="To delight every guest with unforgettable flavors and warm hospitality.",
            vision_title="Our Vision", vision="To be the most loved restaurant brand in the city.",
            chef_name="Chef Marco", chef_title="Head Chef", chef_bio="With over 20 years of experience, Chef Marco crafts dishes that tell a story.",
            stat1_label="Years Experience", stat1_value="15+", stat2_label="Menu Items", stat2_value="50+",
            stat3_label="Happy Customers", stat3_value="10K+", stat4_label="Rating", stat4_value="4.9/5",
        ))
    db.session.commit()

    # ---- Admin user ----
    admin_role = Role.query.filter_by(name="ADMIN").first()
    if not User.query.filter_by(username="admin").first():
        admin_user = User(username="admin", email="admin@savorybites.com", role_id=admin_role.id, status="active")
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(Staff(user_id=admin_user.id, full_name="System Administrator",
                             phone="+1 000 000 0000", address="Head Office",
                             profile_image="uploads/staff/default.png", joining_date=date.today()))
        db.session.commit()

    # ---- Sample staff ----
    roles_map = {r.name: r for r in Role.query.all()}
    sample_staff = [
        ("manager1", "manager@savorybites.com", "Olivia Manager", "MANAGER", "manager123"),
        ("waiter1", "waiter@savorybites.com", "Liam Waiter", "WAITER", "waiter123"),
        ("chef1", "chef@savorybites.com", "Marco Chef", "CHEF", "chef123"),
    ]
    for uname, email, name, rname, pw in sample_staff:
        if not User.query.filter_by(username=uname).first():
            u = User(username=uname, email=email, role_id=roles_map[rname].id, status="active")
            u.set_password(pw)
            db.session.add(u)
            db.session.flush()
            db.session.add(Staff(user_id=u.id, full_name=name, phone="+1 200 300 4000",
                                 profile_image="uploads/staff/default.png", joining_date=date.today()))
    db.session.commit()

    # ---- Categories ----
    cat_data = ["Burgers", "Pizza", "Pasta", "Chicken", "Rice", "Desserts", "Drinks", "Fast Food"]
    cat_objs = {}
    for i, c in enumerate(cat_data):
        existing = Category.query.filter_by(name=c).first()
        if not existing:
            existing = Category(name=c, slug=c.lower().replace(" ", "-"),
                                description=f"{c} category", display_order=i, status="active")
            db.session.add(existing)
            db.session.flush()
        cat_objs[c] = existing
    db.session.commit()

    # ---- Menu items ----
    menu_data = [
        ("Classic Beef Burger", "Burgers", 12.99, 10, "Juicy beef patty with fresh veggies.", True),
        ("Cheese Burger", "Burgers", 13.99, 0, "Beef burger with melted cheese.", False),
        ("Margherita Pizza", "Pizza", 14.99, 0, "Tomato, mozzarella and basil.", True),
        ("Pepperoni Pizza", "Pizza", 16.99, 5, "Loaded with pepperoni.", False),
        ("Spaghetti Carbonara", "Pasta", 13.49, 0, "Creamy Italian pasta.", False),
        ("Grilled Chicken", "Chicken", 15.99, 0, "Perfectly grilled chicken breast.", True),
        ("Fried Chicken Bucket", "Chicken", 19.99, 8, "Crispy fried chicken.", False),
        ("Chicken Fried Rice", "Rice", 11.99, 0, "Flavorful fried rice with chicken.", False),
        ("Veggie Fried Rice", "Rice", 10.99, 0, "Healthy vegetable fried rice.", False),
        ("Chocolate Lava Cake", "Desserts", 6.99, 0, "Warm chocolate cake.", True),
        ("Vanilla Ice Cream", "Desserts", 4.99, 0, "Creamy vanilla ice cream.", False),
        ("Fresh Lemonade", "Drinks", 3.99, 0, "Refreshing lemonade.", False),
        ("Coca Cola", "Drinks", 2.99, 0, "Chilled soft drink.", False),
        ("French Fries", "Fast Food", 4.49, 0, "Crispy golden fries.", True),
        ("Chicken Nuggets", "Fast Food", 6.49, 0, "Tender chicken nuggets.", False),
    ]
    for name, cat, price, disc, desc, feat in menu_data:
        if not MenuItem.query.filter_by(name=name).first():
            db.session.add(MenuItem(
                name=name, slug=name.lower().replace(" ", "-"),
                category_id=cat_objs[cat].id, description=desc, price=price, discount=disc,
                preparation_time=15, availability="available", featured=feat,
                rating=4.5, rating_count=10, display_order=0, status="active",
                image="uploads/products/default.png",
            ))
    db.session.commit()

    # ---- Tables ----
    if RestaurantTable.query.count() == 0:
        for i in range(1, 13):
            status = "available"
            if i in (3, 7):
                status = "occupied"
            elif i == 5:
                status = "reserved"
            db.session.add(RestaurantTable(table_number=f"T{i:02d}", capacity=4 if i % 3 else 2,
                                           status=status, location="indoor"))
        db.session.commit()

    # ---- Suppliers & Inventory ----
    if Supplier.query.count() == 0:
        s1 = Supplier(name="Fresh Farms", company="Fresh Farms Co.", phone="+1 111 222 3333",
                      email="supplies@freshfarms.com", products="Vegetables, Chicken, Meat")
        s2 = Supplier(name="Bakery Plus", company="Bakery Plus Ltd.", phone="+1 444 555 6666",
                      email="hello@bakeryplus.com", products="Flour, Cheese, Bread")
        db.session.add_all([s1, s2])
        db.session.commit()
        inv = [
            ("Chicken", "meat", 50, "kg", 20, 6.0, s1.id),
            ("Flour", "bakery", 30, "kg", 10, 1.5, s2.id),
            ("Cheese", "dairy", 8, "kg", 15, 4.0, s2.id),
            ("Tomatoes", "vegetables", 5, "kg", 12, 2.0, s1.id),
            ("Vegetable Oil", "oil", 40, "L", 10, 3.0, s1.id),
        ]
        for name, cat, qty, unit, minq, price, sid in inv:
            item = InventoryItem(name=name, category=cat, quantity=qty, unit=unit,
                                  minimum_stock=minq, purchase_price=price, supplier_id=sid)
            item.update_status()
            db.session.add(item)
        db.session.commit()

    # ---- Services ----
    if Service.query.count() == 0:
        services = [
            ("Dine-In", "Enjoy your meal in our elegant dining hall.", "utensils", "Learn More", "/reservation", 1),
            ("Takeaway", "Order online and pick up fresh.", "shopping-bag", "Order Now", "/menu", 2),
            ("Home Delivery", "Hot food delivered to your door.", "truck", "Order Now", "/menu", 3),
            ("Catering", "Premium catering for events.", "users", "Contact Us", "/contact", 4),
            ("Table Reservation", "Reserve your perfect table.", "calendar-check", "Reserve", "/reservation", 5),
            ("Private Dining", "Exclusive spaces for special moments.", "glass-cheers", "Inquire", "/contact", 6),
        ]
        for title, desc, icon, btn, link, order in services:
            db.session.add(Service(title=title, description=desc, icon=icon,
                                   button_text=btn, button_link=link, display_order=order, status="active"))
        db.session.commit()

    # ---- Banners ----
    if Banner.query.count() == 0:
        db.session.add(Banner(
            title="Fresh Taste. Beautiful Moments.",
            description="Experience culinary excellence crafted with passion and the finest ingredients.",
            image="uploads/banners/default.jpg", button_text="Explore Menu", button_link="/menu",
            secondary_button_text="Reserve a Table", secondary_button_link="/reservation",
            display_order=1, status="active",
        ))
        db.session.commit()

    # ---- Offers ----
    if Offer.query.count() == 0:
        db.session.add(Offer(name="Weekend Special", description="20% off all pizzas this weekend.",
                             discount_type="percentage", discount_value=20,
                             start_date=date.today(), end_date=date.today(), status="active", display_order=1))
        db.session.commit()

    # ---- Sample customer ----
    if not User.query.filter_by(username="customer1").first():
        cust_role = roles_map["CUSTOMER"]
        cu = User(username="customer1", email="customer@savorybites.com", role_id=cust_role.id, status="active")
        cu.set_password("customer123")
        db.session.add(cu)
        db.session.flush()
        db.session.add(Customer(user_id=cu.id, full_name="Emma Customer", phone="+1 555 666 7777",
                                profile_image="uploads/customers/default.png"))
        db.session.commit()

    # ---- Sample order ----
    if Order.query.count() == 0:
        table = RestaurantTable.query.filter_by(table_number="T03").first()
        waiter = Staff.query.join(User).filter(User.username == "waiter1").first()
        cust = Customer.query.join(User).filter(User.username == "customer1").first()
        order = Order(order_number=generate_order_number(), order_type="dine_in",
                      customer_id=cust.id if cust else None, table_id=table.id if table else None,
                      waiter_id=waiter.id if waiter else None, subtotal=26.98, discount=0,
                      tax=2.70, delivery_charges=0, total=29.68, order_status="ready",
                      payment_status="paid", special_instructions="No onions")
        db.session.add(order)
        db.session.flush()
        item1 = MenuItem.query.filter_by(name="Classic Beef Burger").first()
        item2 = MenuItem.query.filter_by(name="Fresh Lemonade").first()
        db.session.add(OrderItem(order_id=order.id, menu_item_id=item1.id, quantity=2,
                                 unit_price=item1.price, discount=item1.discount, status="ready"))
        if item2:
            db.session.add(OrderItem(order_id=order.id, menu_item_id=item2.id, quantity=1,
                                     unit_price=item2.price, discount=0, status="ready"))
        db.session.add(KitchenOrder(order_id=order.id, status="ready", ready_at=datetime.utcnow()))
        db.session.commit()

    print("Seed complete.")
