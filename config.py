import os
from datetime import timedelta


class Config:
    """Base configuration. Sensitive values are loaded from environment / .env."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-to-a-secure-random-key")
    # SQLite database for development and production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///restaurant.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite doesn't need connection pooling options

    # Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "ico"}

    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # set True behind HTTPS in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Business defaults (overridable via restaurant_settings)
    DEFAULT_CURRENCY = "USD"
    DEFAULT_TAX_RATE = 10.0  # percent


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
