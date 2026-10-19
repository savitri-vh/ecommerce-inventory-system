"""
Application configuration.

Design notes for Postgres migration:
- We never use SQLite-specific types/features in the models (no JSON1 functions,
  no "INTEGER PRIMARY KEY AUTOINCREMENT" tricks, etc.) so the same model
  definitions work unchanged against Postgres.
- DATABASE_URL is read from the environment so switching dev -> prod is just
  an env var change, e.g.:
      postgresql+psycopg2://user:password@localhost:5432/ecommerce_db
- SQLAlchemy's `db.Enum` compiles to a CHECK constraint on SQLite and to a
  native CREATE TYPE ... AS ENUM on Postgres - both are generated from the
  same Python enum, so no code changes are needed when migrating.
"""

import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "app.db")
    )
    # Silence the event system overhead; not needed since we don't use signals.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Helps catch stale-connection issues on Postgres in production; harmless on SQLite.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Flask-WTF CSRF protection is on by default when Flask-WTF is used for forms.
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
