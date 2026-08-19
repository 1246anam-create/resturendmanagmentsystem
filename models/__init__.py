"""Database models package. Import all models so they register with SQLAlchemy."""
from .user import User, Role, Permission, role_permissions, Staff, Customer
from .menu import Category, MenuItem, Review
from .order import Order, OrderItem, KitchenOrder, Payment, Invoice, Delivery
from .table import RestaurantTable, Reservation
from .inventory import InventoryItem, InventoryTransaction, Supplier, Purchase, PurchaseItem
from .settings import (
    Service, Banner, AboutContent, HeaderSettings, FooterSettings,
    RestaurantSettings, ThemeSettings, Notification, ActivityLog, Offer,
)

__all__ = [
    "User", "Role", "Permission", "role_permissions", "Staff", "Customer",
    "Category", "MenuItem", "Review",
    "Order", "OrderItem", "KitchenOrder", "Payment", "Invoice", "Delivery",
    "RestaurantTable", "Reservation",
    "InventoryItem", "InventoryTransaction", "Supplier", "Purchase", "PurchaseItem",
    "Service", "Banner", "AboutContent", "HeaderSettings", "FooterSettings",
    "RestaurantSettings", "ThemeSettings", "Notification", "ActivityLog", "Offer",
]
