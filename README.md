# Savory Bites — Restaurant Management System

A full-stack Restaurant Management System built with **Flask** (Python) and
**PostgreSQL** (SQLite fallback for local testing). It combines a public
restaurant website/CMS, an admin control panel, a waiter POS, a kitchen display
system (KDS), and role-based staff/customer management.

## Features

- **5 roles with RBAC**: ADMIN, MANAGER, WAITER, CHEF, CUSTOMER. Permissions are
  enforced on the backend (not just hidden in the UI).
- **Public website**: Home, About, Menu, Services, Reservation, Contact, Login,
  Register — fully driven by CMS content.
- **Admin control panel**: dashboard with charts (sales, popular food, payment
  methods, table occupancy, inventory usage), staff & customer management, menu
  & categories, orders, tables, reservations, billing & invoices, payments,
  inventory, suppliers, purchases, delivery, offers, reviews, reports,
  analytics, notifications, activity logs.
- **CMS**: manage header, hero banners, services, about page, restaurant info,
  theme (CSS variables, light/dark), logo & favicon — without editing code.
- **Manager dashboard**: operations-focused view (orders, tables, reservations,
  inventory, suppliers, purchases, reports, staff).
- **Waiter POS**: touch-friendly order creation, cart, table assignment,
  serving & payment.
- **Kitchen Display System (KDS)**: live order columns
  (New → Accepted → Preparing → Ready) with one-click status updates via JSON API.
- **Customer portal**: dashboard, order history, reservations, profile, reviews.
- **Security**: Flask-Login sessions, password hashing (Werkzeug), CSRF
  protection (Flask-WTF), secure uploads, secrets via `.env`. Passwords are
  never stored in plaintext.

## Tech Stack

- Backend: Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- Database: PostgreSQL (default) / SQLite (local fallback)
- Frontend: HTML5, CSS3 (CSS variables, light/dark theme), vanilla JS (Fetch/AJAX),
  Chart.js (CDN) for dashboards
- Auth: session-based with RBAC decorators (`permission_required`, `role_required`)

## Project Structure

```
app.py                 # Application factory + CLI (init-db)
config.py              # Config classes (dev/prod/test)
extensions.py          # db, login_manager, csrf
models/                # SQLAlchemy models (user, menu, order, table, inventory, settings)
routes/                # Blueprints: auth, admin, manager, waiter, chef, customer, public, cms, api
templates/             # Jinja2 templates per role + base layouts + CMS + errors
static/                # css/style.css, js/main.js, uploads/
seed.py                # Default data + sample records
requirements.txt
.env                   # Secrets & DB URL
```

## Setup

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (`.env`):
   ```ini
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/restaurant_db
   FLASK_ENV=development
   ```
   > If PostgreSQL is not installed, the app falls back to SQLite automatically
   > when `DATABASE_URL` is not set, or you can set
   > `DATABASE_URL=sqlite:///restaurant.db`.

4. **Initialize and seed the database**:
   ```bash
   flask init-db
   ```
   This creates all tables, the five system roles + permission catalogue, and
   seeds sample data (admin, staff, menu, tables, inventory, CMS content).

5. **Run the app**:
   ```bash
   flask run
   # or
   python app.py
   ```
   Open http://localhost:5000

## Default Login Credentials

| Role     | Username    | Password      |
|----------|-------------|---------------|
| Admin    | `admin`     | `admin123`    |
| Manager  | `manager1`  | `manager123`  |
| Waiter   | `waiter1`   | `waiter123`   |
| Chef     | `chef1`     | `chef123`     |
| Customer | `customer1` | `customer123` |

> Change these passwords after first login in a production environment.

## Key URLs

- Public site: `/`, `/menu`, `/reservation`, `/about`, `/services`, `/contact`
- Admin: `/admin/`
- Manager: `/manager/`
- Waiter POS: `/waiter/`
- Kitchen (KDS): `/chef/`
- Customer: `/customer/`
- JSON API (KDS/polling): `/kitchen/orders`, `/tables/status`, `/notifications`

## Notes

- The KDS and dashboards poll JSON endpoints under the `/api` blueprint
  (CSRF-exempt) for live updates.
- Theme switching (light/dark) is persisted via `localStorage` and can be set
  server-side through the CMS theme settings.
- All uploads go to `static/uploads` with extension validation.
