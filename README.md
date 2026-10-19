# E-Commerce & Inventory Management System

Full-stack Flask app: product catalog, cart/checkout, order history, and an
admin dashboard with stock management and sales charts. SQLite for
development, schema designed to migrate to PostgreSQL with no model changes
(see `config.py` for details).

**Status: Phases 1–3 complete.** Auth, product catalog (search/filter), admin
product CRUD, session cart, and transactional checkout are built and tested.
Phases 4–6 (order history, admin dashboard, polish) are not yet implemented.

## Tech stack

- Backend: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- DB: SQLite (dev) → PostgreSQL (prod), same models
- Frontend: Jinja2 templates, vanilla CSS/JS, Chart.js (Phase 5+)
- Passwords: hashed with `werkzeug.security`

## Project layout

```
ecommerce_app/
├── app/
│   ├── __init__.py          # app factory
│   ├── extensions.py        # db, login_manager singletons
│   ├── models.py            # all 7 SQLAlchemy models
│   ├── forms.py             # Flask-WTF forms
│   ├── cart.py              # session-based cart helpers
│   ├── decorators.py        # @admin_required
│   ├── blueprints/
│   │   ├── auth.py          # register / login / logout
│   │   ├── customer.py      # catalog, product detail, cart, checkout
│   │   └── admin.py         # product CRUD
│   ├── templates/
│   │   ├── base.html        # navbar (role-aware), flash messages, cart badge
│   │   ├── errors/           # 403.html, 404.html
│   │   ├── auth/             # login.html, register.html
│   │   ├── customer/         # catalog.html, product_detail.html, cart.html
│   │   └── admin/            # product_list.html, product_form.html
│   └── static/css/style.css
├── config.py                 # Dev/Prod/Testing config, DATABASE_URL
├── seed.py                   # creates tables + admin/customer/sample data
├── run.py                    # entrypoint
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd ecommerce_app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # edit SECRET_KEY etc. if desired

python seed.py                  # creates app.db and seeds data
# use `python seed.py --reset` to wipe and reseed

python run.py                   # starts dev server on http://127.0.0.1:5000
```

Seeded accounts:

| Role     | Email                 | Password          |
|----------|-----------------------|-------------------|
| Admin    | admin@eshop.example   | AdminPass123!     |
| Customer | jane@eshop.example    | CustomerPass123!  |

(Change these immediately if you deploy this anywhere real.)

## Migrating to PostgreSQL later

1. `pip install psycopg2-binary`
2. Set `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname` in `.env`
3. Run `python seed.py` (or your migration tool of choice) against the new DB.

No model or query changes are required — see the comments at the top of
`app/models.py` and `config.py` for the specific portability choices made
(Numeric for money, Python-side enums, `pool_pre_ping`, etc.).

## Database schema (Phase 1)

7 tables: `users`, `categories`, `products`, `inventory` (1:1 with products),
`orders`, `order_items`, `stock_movements`. Indexes beyond primary keys:
unique indexes on `users.email`, `categories.name`, `products.sku`,
`inventory.product_id`; plus indexes on every foreign key
(`products.category_id`, `orders.user_id`, `order_items.order_id/product_id`,
`stock_movements.product_id`) and on `orders.status`, `orders.created_at`,
and `stock_movements.reason/timestamp` for the Phase 5 dashboard queries.

## Cart & checkout (Phase 3)

The cart lives in the Flask session (`{product_id: quantity}`), so browsing
and adding to cart work without an account — only `/shop/checkout` requires
login. Checkout (`app/blueprints/customer.py::checkout`) is a single
SQLAlchemy transaction:

1. Create the `Order` (status `pending`) and flush to get its id.
2. For every cart line: re-check live `Inventory.stock_qty` (it may have
   changed since the item was added to the cart), create the `OrderItem`,
   decrement stock, and log a `StockMovement` (`reason='sale'`).
3. If **any** line has insufficient stock, `db.session.rollback()` discards
   the whole transaction — the Order, every OrderItem, every inventory
   decrement, every StockMovement — and the shopper sees exactly which
   item(s) are short. Nothing partially succeeds.
4. Only if every line clears does the Order flip to `confirmed` and commit.

This is covered by an automated test that forces a stock shortage on one
line of a two-item cart and asserts the *other*, otherwise-valid line is
also rolled back (see commit history / ask for the test script).

## What's next

- **Phase 4**: customer order history ("My Orders" list + order detail view)
- **Phase 5**: admin dashboard (stock table, restock action, Chart.js charts from raw SQL)
- **Phase 6**: validation polish, flash messages everywhere, responsive CSS, final README
