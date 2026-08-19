"""Centralized Flask extensions so models and routes can share them."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Login manager configuration
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
login_manager.session_protection = "strong"
