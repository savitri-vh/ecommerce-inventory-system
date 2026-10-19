"""
Session-based shopping cart helpers.

The cart lives entirely in the Flask session as {str(product_id): quantity}.
Session data must be JSON-serializable, hence string keys even though
product ids are ints internally.

This module only touches the session and reads Product/Inventory for
display/validation — it never writes to the database. All DB writes
(Order, OrderItem, Inventory, StockMovement) happen in the checkout view,
inside one transaction, so a half-finished cart never corrupts stock data.
"""

from decimal import Decimal

from flask import session

from app.models import Product

CART_SESSION_KEY = "cart"


def _get_raw_cart():
    return session.setdefault(CART_SESSION_KEY, {})


def add_item(product_id, quantity=1):
    """
    Adds `quantity` of a product to the cart (additive if already present).
    Clamps to available stock so the cart never knowingly holds more than
    what's in stock at add-time (checkout still re-validates, since stock
    can change between add-to-cart and checkout).
    Returns (success: bool, message: str).
    """
    product = Product.query.get(product_id)
    if not product:
        return False, "That product no longer exists."

    quantity = max(1, int(quantity))
    cart = _get_raw_cart()
    key = str(product_id)
    current_qty = cart.get(key, 0)
    new_qty = current_qty + quantity

    available = product.inventory.stock_qty if product.inventory else 0
    if available <= 0:
        return False, f"{product.name} is out of stock."

    if new_qty > available:
        new_qty = available
        cart[key] = new_qty
        session.modified = True
        return True, f"Only {available} of {product.name} available — added what's in stock."

    cart[key] = new_qty
    session.modified = True
    return True, f"Added {quantity} x {product.name} to your cart."


def update_item(product_id, quantity):
    """Sets (not adds) the quantity for a product already in the cart."""
    product = Product.query.get(product_id)
    if not product:
        return False, "That product no longer exists."

    quantity = int(quantity)
    cart = _get_raw_cart()
    key = str(product_id)

    if quantity <= 0:
        cart.pop(key, None)
        session.modified = True
        return True, f"Removed {product.name} from your cart."

    available = product.inventory.stock_qty if product.inventory else 0
    if quantity > available:
        quantity = available

    if quantity <= 0:
        cart.pop(key, None)
        session.modified = True
        return False, f"{product.name} is out of stock."

    cart[key] = quantity
    session.modified = True
    return True, f"Updated {product.name} quantity to {quantity}."


def remove_item(product_id):
    cart = _get_raw_cart()
    cart.pop(str(product_id), None)
    session.modified = True


def clear_cart():
    session[CART_SESSION_KEY] = {}
    session.modified = True


def get_cart_items():
    """
    Returns a list of dicts for display: product, quantity, line_total,
    and whether the requested quantity now exceeds available stock
    (prices/stock can change after items were added).
    """
    cart = _get_raw_cart()
    items = []
    for product_id_str, quantity in cart.items():
        product = Product.query.get(int(product_id_str))
        if not product:
            continue
        available = product.inventory.stock_qty if product.inventory else 0
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": product.price * quantity,
                "available": available,
                "insufficient_stock": quantity > available,
            }
        )
    return items


def get_cart_count():
    """Total number of units in the cart, for the navbar badge."""
    return sum(_get_raw_cart().values())


def get_cart_total(items=None):
    items = items if items is not None else get_cart_items()
    return sum((item["line_total"] for item in items), Decimal("0.00"))
