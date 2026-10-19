"""
SQLAlchemy models for the E-commerce & Inventory Management System.

Portability (SQLite -> PostgreSQL) notes:
- All primary keys use db.Integer (maps to SERIAL/IDENTITY on Postgres, and to
  SQLite's native rowid autoincrement) rather than any SQLite-only trick.
- All enums are declared with Python's `enum.Enum` + SQLAlchemy's `db.Enum`,
  which SQLAlchemy renders as a CHECK constraint on SQLite and a native
  CREATE TYPE ... AS ENUM on Postgres. The `values_callable` kwarg ensures the
  *string values* (not the Python member names) are what gets stored/compared,
  which keeps the stored data human-readable and stable across DB backends.
- Monetary columns use db.Numeric(10, 2) rather than Float, because floating
  point is unsafe for currency and Numeric maps cleanly to Postgres' NUMERIC.
- Timestamps use db.DateTime with a Python-side default (datetime.utcnow)
  rather than a DB-side server_default, so behavior is identical on both
  SQLite and Postgres without relying on backend-specific functions.
- `db.ForeignKey` + explicit `index=True` is used on every FK column: SQLite
  does NOT automatically index FK columns (unlike some other databases), and
  neither does Postgres, so we index them explicitly for join performance.
"""

import enum
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class StockMovementReason(enum.Enum):
    SALE = "sale"
    RESTOCK = "restock"
    RETURN = "return"
    ADJUSTMENT = "adjustment"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(UserRole, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserRole.CUSTOMER,
        server_default=UserRole.CUSTOMER.value,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # One user -> many orders.
    orders = db.relationship(
        "Order", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    # --- password helpers -------------------------------------------------
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # --- role helpers -------------------------------------------------
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    def __repr__(self):
        return f"<User {self.id} {self.email} ({self.role.value})>"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.id} {self.name}>"


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    sku = db.Column(db.String(64), nullable=False, unique=True, index=True)

    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # One product -> one inventory row.
    inventory = db.relationship(
        "Inventory",
        backref="product",
        uselist=False,
        lazy=True,
        cascade="all, delete-orphan",
    )
    order_items = db.relationship("OrderItem", backref="product", lazy=True)
    stock_movements = db.relationship(
        "StockMovement", backref="product", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.id} {self.name} ({self.sku})>"


# ---------------------------------------------------------------------------
# Inventory  (one-to-one with Product)
# ---------------------------------------------------------------------------

class Inventory(db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)
    # unique=True enforces the one-to-one relationship at the DB level.
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False, unique=True, index=True
    )
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    reorder_threshold = db.Column(db.Integer, nullable=False, default=10)

    @property
    def is_low_stock(self):
        return self.stock_qty <= self.reorder_threshold

    def __repr__(self):
        return f"<Inventory product_id={self.product_id} qty={self.stock_qty}>"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(
        db.Enum(OrderStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        index=True,  # dashboard filters/groups orders by status frequently
    )
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    # ^ indexed because the revenue-over-time dashboard query filters/groups by date range

    items = db.relationship(
        "OrderItem", backref="order", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.id} user={self.user_id} status={self.status.value}>"


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    # Price captured at purchase time so historical orders stay accurate even
    # if Product.price changes later.
    price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False)

    @property
    def line_total(self):
        return self.quantity * self.price_at_purchase

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# StockMovement  (audit trail for every inventory change)
# ---------------------------------------------------------------------------

class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    # Positive for additions (restock, return), negative for removals (sale).
    change_qty = db.Column(db.Integer, nullable=False)
    reason = db.Column(
        db.Enum(StockMovementReason, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,  # dashboard/report queries often group by reason
    )
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    note = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<StockMovement product={self.product_id} {self.change_qty} ({self.reason.value})>"
