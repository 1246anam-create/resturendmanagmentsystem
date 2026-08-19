"""Application factory and entry point for the Restaurant Management System."""
import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template
from extensions import db, login_manager, csrf
from models import *  # noqa: F401,F403  (registers all models)
from utils.auth import create_default_roles_and_permissions
from models.settings import (
    RestaurantSettings, ThemeSettings, HeaderSettings, FooterSettings,
)

load_dotenv()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")
    from config import config_by_name

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure upload folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from routes.auth import bp as auth_bp
    from routes.admin import bp as admin_bp
    from routes.manager import bp as manager_bp
    from routes.waiter import bp as waiter_bp
    from routes.chef import bp as chef_bp
    from routes.customer import bp as customer_bp
    from routes.public import bp as public_bp
    from routes.cms import bp as cms_bp
    from routes.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(waiter_bp)
    app.register_blueprint(chef_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    # Context processors: expose settings & helpers to all templates
    @app.context_processor
    def inject_globals():
        theme = ThemeSettings.query.first()
        restaurant = RestaurantSettings.query.first()
        header = HeaderSettings.query.first()
        footer = FooterSettings.query.first()
        return dict(
            theme=theme,
            restaurant=restaurant,
            header=header,
            footer=footer,
            now=datetime.utcnow(),
        )

    @app.template_filter("currency")
    def currency_filter(amount):
        r = RestaurantSettings.query.first()
        sym = r.currency_symbol if r and r.currency_symbol else "$"
        return f"{sym}{float(amount or 0):,.2f}"

    @app.template_filter("status_badge")
    def status_badge(status):
        mapping = {
            "active": "success", "available": "success", "paid": "success",
            "confirmed": "success", "completed": "success", "ready": "success",
            "in_stock": "success", "approved": "success",
            "pending": "warning", "reserved": "warning", "preparing": "warning",
            "low_stock": "warning", "partially_paid": "warning", "new": "warning",
            "inactive": "secondary", "unavailable": "secondary", "out_of_service": "secondary",
            "cancelled": "danger", "out_of_stock": "danger", "expired": "danger",
            "rejected": "danger", "refunded": "danger", "closed": "danger",
            "accepted": "info", "served": "info", "delivered": "info",
            "out_for_delivery": "info",
        }
        return mapping.get(status, "secondary")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # CLI / init
    @app.cli.command("init-db")
    def init_db_command():
        """Create tables and seed default data."""
        with app.app_context():
            db.create_all()
            create_default_roles_and_permissions()
            from seed import seed_all
            seed_all()
        print("Database initialized and seeded.")

    return app


# Login manager user loader
from models.user import User  # noqa: E402


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
