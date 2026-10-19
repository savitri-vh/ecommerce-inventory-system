"""
Customer-facing blueprint: product catalog, product detail, session cart,
and transactional checkout. Order history (Phase 4) will be added to this
same blueprint.
"""

from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import cart as cart_service
from app.extensions import db
from app.models import Product, Category, Order, OrderItem, StockMovement, OrderStatus, StockMovementReason

customer_bp = Blueprint("customer", __name__, url_prefix="/shop")


@customer_bp.route("/")
def catalog():
    """
    Product listing with optional category filter (?category_id=) and
    name search (?q=). Both are optional and can be combined.
    """
    query = Product.query

    search_term = request.args.get("q", "").strip()
    if search_term:
        # Case-insensitive partial match on product name.
        query = query.filter(Product.name.ilike(f"%{search_term}%"))

    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.order_by(Product.name.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        "customer/catalog.html",
        products=products,
        categories=categories,
        search_term=search_term,
        selected_category_id=category_id,
    )


@customer_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("customer/product_detail.html", product=product)


# ---------------------------------------------------------------------------
# Cart (session-based; works for anonymous browsers too, same as most shops —
# only checkout itself requires being logged in)
# ---------------------------------------------------------------------------

@customer_bp.route("/cart")
def view_cart():
    items = cart_service.get_cart_items()
    total = cart_service.get_cart_total(items)
    return render_template("customer/cart.html", items=items, total=total)


@customer_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    quantity = request.form.get("quantity", 1, type=int) or 1
    success, message = cart_service.add_item(product_id, quantity)
    flash(message, "success" if success else "danger")

    # Send the shopper back wherever they clicked "Add to Cart" from.
    next_url = request.form.get("next") or url_for("customer.catalog")
    return redirect(next_url)


@customer_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart_item(product_id):
    quantity = request.form.get("quantity", 0, type=int) or 0
    success, message = cart_service.update_item(product_id, quantity)
    flash(message, "success" if success else "danger")
    return redirect(url_for("customer.view_cart"))


@customer_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart_service.remove_item(product_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("customer.view_cart"))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@customer_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    """
    Converts the session cart into a confirmed Order, inside a single DB
    transaction:
        1. Create the Order (status=PENDING) and flush to get its id.
        2. For every cart line, re-check live stock (it may have changed
           since the item was added to the cart), create the OrderItem,
           decrement Inventory.stock_qty, and log a StockMovement
           (reason='sale').
        3. If ANY line has insufficient stock, the whole transaction is
           rolled back — no Order, no OrderItems, no inventory changes —
           and the shopper sees exactly which item(s) are the problem.
        4. Only if every line succeeds do we set the Order to CONFIRMED
           and commit.
    """
    items = cart_service.get_cart_items()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.view_cart"))

    order = Order(user_id=current_user.id, status=OrderStatus.PENDING, total_amount=Decimal("0.00"))

    try:
        db.session.add(order)
        db.session.flush()  # assign order.id for the OrderItem/StockMovement rows below

        stock_errors = []
        running_total = Decimal("0.00")

        for item in items:
            product = item["product"]
            quantity = item["quantity"]
            inventory = product.inventory

            if not inventory or inventory.stock_qty < quantity:
                available = inventory.stock_qty if inventory else 0
                stock_errors.append(
                    f"{product.name}: only {available} left in stock (you requested {quantity})."
                )
                continue

            inventory.stock_qty -= quantity

            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price_at_purchase=product.price,
                )
            )
            db.session.add(
                StockMovement(
                    product_id=product.id,
                    change_qty=-quantity,
                    reason=StockMovementReason.SALE,
                    note=f"Sale — order #{order.id}",
                )
            )
            running_total += product.price * quantity

        if stock_errors:
            # Not enough stock for at least one line: discard the entire
            # transaction (new Order, all OrderItems, all Inventory
            # decrements, all StockMovements) rather than a partial order.
            db.session.rollback()
            for msg in stock_errors:
                flash(msg, "danger")
            flash("Checkout failed — one or more items are out of stock. Please update your cart.", "danger")
            return redirect(url_for("customer.view_cart"))

        order.total_amount = running_total
        order.status = OrderStatus.CONFIRMED
        db.session.commit()

    except Exception:
        db.session.rollback()
        flash("Something went wrong during checkout. Your cart has not been charged — please try again.", "danger")
        return redirect(url_for("customer.view_cart"))

    cart_service.clear_cart()
    flash(f"Order #{order.id} placed successfully! Total: ${running_total:.2f}", "success")
    return redirect(url_for("customer.catalog"))
