"""Download real food photos for each menu item and update the database.

Uses loremflickr.com (free Creative Commons photos, no API key). Falls back to
the existing placeholder if a download fails, so the menu never breaks.

Run from the project root:
    python download_menu_images.py
"""
import os
import urllib.parse
import urllib.request

from app import app
from models.menu import MenuItem
from models.user import db

OUT_DIR = os.path.join("static", "uploads", "products")

# Search query per menu item id (keyword used to fetch a relevant photo).
QUERY = {
    1: "beef,burger",
    2: "cheeseburger",
    3: "margherita,pizza",
    4: "pepperoni,pizza",
    5: "spaghetti,carbonara",
    6: "grilled,chicken",
    7: "fried,chicken",
    8: "chicken,fried,rice",
    9: "vegetable,fried,rice",
    10: "chocolate,lava,cake",
    11: "vanilla,ice,cream",
    12: "lemonade,drink",
    13: "cola,drink",
    14: "french,fries",
    15: "chicken,nuggets",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def download(query, dest):
    url = "https://loremflickr.com/800/600/" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read()
    if not data or len(data) < 2000:
        return False
    # Basic sanity: JPEG/PNG magic bytes.
    if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n":
        with open(dest, "wb") as f:
            f.write(data)
        return True
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with app.app_context():
        for item in MenuItem.query.all():
            q = QUERY.get(item.id, item.name or "food")
            safe = f"item_{item.id}.jpg"
            dest = os.path.join(OUT_DIR, safe)
            try:
                ok = download(q, dest)
            except Exception as e:
                print(f"  SKIP {item.name}: {e}")
                ok = False
            if ok:
                item.image = f"uploads/products/{safe}"
                print(f"  OK   {item.name}: {item.image}")
            else:
                print(f"  KEEP {item.name}: kept existing {item.image}")
        db.session.commit()
    print("Done.")


if __name__ == "__main__":
    main()
