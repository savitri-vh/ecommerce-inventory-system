"""
Centralized Flask extension instances.

Kept in their own module (instead of inside app/__init__.py) so that
models.py and blueprint modules can import `db` / `login_manager` without
causing circular imports with the app factory.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# Where Flask-Login redirects anonymous users who hit an @login_required view.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
