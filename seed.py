"""
Seed script.

Creates the database tables (if they don't exist) and populates:
- One admin user
- A few sample categories
- A few sample products, each with a matching Inventory row

Usage:
    python seed.py            # seed only if DB is empty
    python seed.py --reset    # drop all tables and reseed from scratch
"""

import sys

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Category, Product, Inventory


ADMIN_EMAIL = "admin@eshop.example"
ADMIN_PASSWORD = "AdminPass123!"  # change immediately after first login in real use


def seed():
    app = create_app()

    with app.app_context():
        if "--reset" in sys.argv:
            print("Dropping all tables...")
            db.drop_all()

        print("Creating tables...")
        db.create_all()

        if User.query.filter_by(email=ADMIN_EMAIL).first():
            print("Database already seeded (admin user exists). Skipping.")
            return

        # --- Admin user -----------------------------------------------------
        admin = User(name="Store Admin", email=ADMIN_EMAIL, role=UserRole.ADMIN)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)

        # --- Sample customer (handy for manual testing) ----------------------
        customer = User(name="Jane Customer", email="jane@eshop.example", role=UserRole.CUSTOMER)
        customer.set_password("CustomerPass123!")
        db.session.add(customer)

        # --- Categories -------------------------------------------------------
        electronics = Category(name="Electronics", description="Gadgets, devices, and accessories.")
        books = Category(name="Books", description="Fiction, non-fiction, and reference.")
        home = Category(name="Home & Kitchen", description="Appliances and household goods.")
        db.session.add_all([electronics, books, home])
        db.session.flush()  # assign IDs without committing yet

        # --- Products + Inventory ----------------------------------------------
        products_data = [
            dict(
                name="Wireless Mouse",
                description="Ergonomic 2.4GHz wireless mouse.",
                price="19.99",
                sku="ELEC-MOUSE-001",
                category_id=electronics.id,
                stock_qty=50,
                reorder_threshold=10,
            ),
            dict(
                name="Mechanical Keyboard",
                description="RGB backlit mechanical keyboard, blue switches.",
                price="59.99",
                sku="ELEC-KEYB-002",
                category_id=electronics.id,
                stock_qty=8,  # intentionally low to demo low-stock highlighting
                reorder_threshold=10,
            ),
            dict(
                name="USB-C Hub",
                description="7-in-1 USB-C hub with HDMI and card reader.",
                price="34.50",
                sku="ELEC-HUB-003",
                category_id=electronics.id,
                stock_qty=25,
                reorder_threshold=5,
            ),
            dict(
                name="The Pragmatic Programmer",
                description="Classic software craftsmanship book.",
                price="42.00",
                sku="BOOK-PRAGPROG-001",
                category_id=books.id,
                stock_qty=15,
                reorder_threshold=5,
            ),
            dict(
                name="Atomic Habits",
                description="Bestselling book on building good habits.",
                price="18.75",
                sku="BOOK-ATOMIC-002",
                category_id=books.id,
                stock_qty=30,
                reorder_threshold=8,
            ),
            dict(
                name="Stainless Steel Blender",
                description="900W countertop blender with 5 speeds.",
                price="79.99",
                sku="HOME-BLEND-001",
                category_id=home.id,
                stock_qty=4,  # intentionally low
                reorder_threshold=6,
            ),
            dict(
                name="Non-Stick Pan Set",
                description="3-piece non-stick frying pan set.",
                price="45.00",
                sku="HOME-PANSET-002",
                category_id=home.id,
                stock_qty=20,
                reorder_threshold=5,
            ),
        ]

        for data in products_data:
            product = Product(
                name=data["name"],
                description=data["description"],
                price=data["price"],
                sku=data["sku"],
                category_id=data["category_id"],
            )
            db.session.add(product)
            db.session.flush()  # get product.id before creating Inventory

            inventory = Inventory(
                product_id=product.id,
                stock_qty=data["stock_qty"],
                reorder_threshold=data["reorder_threshold"],
            )
            db.session.add(inventory)

        db.session.commit()

        print("Seed complete.")
        print(f"  Admin login:    {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Customer login: jane@eshop.example / CustomerPass123!")
        print(f"  Categories: {Category.query.count()}  Products: {Product.query.count()}")


if __name__ == "__main__":
    seed()
