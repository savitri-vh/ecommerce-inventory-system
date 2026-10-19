"""
Application factory.

Using the factory pattern (create_app) rather than a single global `app`
keeps the project testable (TestingConfig spins up an isolated in-memory DB)
and avoids circular imports between extensions, models and blueprints.
"""

import os

from flask import Flask

from config import config_by_name
from app.extensions import db, login_manager


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name[config_name])

    # --- init extensions ---------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    # --- user loader (required by Flask-Login) -----------------------------
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- register blueprints ------------------------------------------------
    from app.blueprints.auth import auth_bp
    from app.blueprints.customer import customer_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    # --- error handlers ------------------------------------------------------
    from flask import render_template as _render_template

    @app.errorhandler(403)
    def forbidden(e):
        return _render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return _render_template("errors/404.html"), 404

    # Phase 3+ blueprints (cart/checkout live on customer_bp; admin dashboard
    # on admin_bp) will extend the modules already registered above.

    # --- template-wide helpers ----------------------------------------------
    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from flask import has_request_context
        from app import cart as cart_service

        context = {"current_year": datetime.utcnow().year}
        if has_request_context():
            context["cart_count"] = cart_service.get_cart_count()
        return context

    return app
