"""Generate clean SVG placeholder images for each menu item so the public
menu page displays proper, consistent images instead of a tiny default icon.

Run from the project root:
    python generate_menu_images.py
"""
import os
from app import app
from models.menu import MenuItem

OUT_DIR = os.path.join("static", "uploads", "products")

# Emoji + accent color per menu item id (falls back by keyword match).
EMOJI_MAP = {
    1: ("🍔", "#c8962a"),   # Classic Beef Burger
    2: ("🍔", "#c8962a"),   # Cheese Burger
    3: ("🍕", "#e07b39"),   # Margherita Pizza
    4: ("🍕", "#e07b39"),   # Pepperoni Pizza
    5: ("🍝", "#d98b3a"),   # Spaghetti Carbonara
    6: ("🍗", "#b5701f"),   # Grilled Chicken
    7: ("🍗", "#b5701f"),   # Fried Chicken Bucket
    8: ("🍚", "#9c7a3c"),   # Chicken Fried Rice
    9: ("🍚", "#7a9c3c"),   # Veggie Fried Rice
    10: ("🍰", "#a85a7a"),  # Chocolate Lava Cake
    11: ("🍨", "#5a8aa8"),  # Vanilla Ice Cream
    12: ("🍹", "#5aa85a"),  # Fresh Lemonade
    13: ("🥤", "#a83a3a"),  # Coca Cola
    14: ("🍟", "#d9a83a"),  # French Fries
    15: ("🍗", "#b5701f"),  # Chicken Nuggets
}

KEYWORD_EMOJI = [
    ("burger", "🍔", "#c8962a"),
    ("pizza", "🍕", "#e07b39"),
    ("spaghetti", "🍝", "#d98b3a"),
    ("pasta", "🍝", "#d98b3a"),
    ("chicken", "🍗", "#b5701f"),
    ("rice", "🍚", "#9c7a3c"),
    ("veggie", "🥗", "#7a9c3c"),
    ("cake", "🍰", "#a85a7a"),
    ("ice cream", "🍨", "#5a8aa8"),
    ("lemonade", "🍹", "#5aa85a"),
    ("cola", "🥤", "#a83a3a"),
    ("fries", "🍟", "#d9a83a"),
    ("nugget", "🍗", "#b5701f"),
]


def resolve(item):
    if item.id in EMOJI_MAP:
        return EMOJI_MAP[item.id]
    name = (item.name or "").lower()
    for kw, emoji, color in KEYWORD_EMOJI:
        if kw in name:
            return (emoji, color)
    return ("🍽️", "#c8962a")


def make_svg(name, emoji, color):
    # Two-tone gradient background derived from the accent color.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="450" viewBox="0 0 600 450">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{color}"/>
      <stop offset="100%" stop-color="#1f1d1b"/>
    </linearGradient>
  </defs>
  <rect width="600" height="450" fill="url(#g)"/>
  <circle cx="300" cy="180" r="110" fill="rgba(255,255,255,0.12)"/>
  <text x="300" y="225" font-size="130" text-anchor="middle" dominant-baseline="central">{emoji}</text>
  <text x="300" y="370" font-size="34" font-family="Poppins, Arial, sans-serif" font-weight="700" fill="#ffffff" text-anchor="middle">{name}</text>
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with app.app_context():
        for item in MenuItem.query.all():
            emoji, color = resolve(item)
            safe = f"item_{item.id}.svg"
            path = os.path.join(OUT_DIR, safe)
            with open(path, "w", encoding="utf-8") as f:
                f.write(make_svg(item.name, emoji, color))
            item.image = f"uploads/products/{safe}"
            print(f"  -> {item.name}: {item.image}")
        from models.user import db
        db.session.commit()
    print("Done. Menu item images generated and saved.")


if __name__ == "__main__":
    main()
