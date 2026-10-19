"""
Admin blueprint: product CRUD for Phase 2. Stock-level dashboard, restock
action, and sales charts (Phase 5) will be added to this same blueprint.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request

from app.extensions import db
from app.decorators import admin_required
from app.forms import ProductForm
from app.models import Product, Category, Inventory, StockMovement, StockMovementReason

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _populate_category_choices(form):
    """SelectField choices must be set at request time (live category list)."""
    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(0, "-- No Category --")] + [(c.id, c.name) for c in categories]


@admin_bp.route("/products")
@admin_required
def list_products():
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template("admin/product_list.html", products=products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def new_product():
    form = ProductForm()
    _populate_category_choices(form)

    if form.validate_on_submit():
        existing = Product.query.filter_by(sku=form.sku.data.strip()).first()
        if existing:
            flash(f"SKU '{form.sku.data}' is already in use by another product.", "danger")
            return render_template("admin/product_form.html", form=form, mode="new")

        product = Product(
            name=form.name.data.strip(),
            description=(form.description.data or "").strip() or None,
            price=form.price.data,
            sku=form.sku.data.strip(),
            category_id=form.category_id.data or None,
        )

        try:
            db.session.add(product)
            db.session.flush()  # assign product.id before creating Inventory

            inventory = Inventory(
                product_id=product.id,
                stock_qty=form.stock_qty.data,
                reorder_threshold=form.reorder_threshold.data,
            )
            db.session.add(inventory)

            if form.stock_qty.data:
                db.session.add(
                    StockMovement(
                        product_id=product.id,
                        change_qty=form.stock_qty.data,
                        reason=StockMovementReason.RESTOCK,
                        note="Initial stock on product creation.",
                    )
                )

            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Something went wrong creating the product. Please try again.", "danger")
            return render_template("admin/product_form.html", form=form, mode="new")

        flash(f"Product '{product.name}' created.", "success")
        return redirect(url_for("admin.list_products"))

    return render_template("admin/product_form.html", form=form, mode="new")


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    _populate_category_choices(form)

    if request.method == "GET":
        form.category_id.data = product.category_id or 0
        if product.inventory:
            form.stock_qty.data = product.inventory.stock_qty
            form.reorder_threshold.data = product.inventory.reorder_threshold

    if form.validate_on_submit():
        existing = Product.query.filter(
            Product.sku == form.sku.data.strip(), Product.id != product.id
        ).first()
        if existing:
            flash(f"SKU '{form.sku.data}' is already in use by another product.", "danger")
            return render_template("admin/product_form.html", form=form, mode="edit", product=product)

        try:
            product.name = form.name.data.strip()
            product.description = (form.description.data or "").strip() or None
            product.price = form.price.data
            product.sku = form.sku.data.strip()
            product.category_id = form.category_id.data or None

            if product.inventory:
                old_qty = product.inventory.stock_qty
                new_qty = form.stock_qty.data
                product.inventory.reorder_threshold = form.reorder_threshold.data

                if new_qty != old_qty:
                    # Manual stock edits during product edit are logged as an
                    # 'adjustment' so the audit trail reflects every change,
                    # distinct from sales/restocks/returns.
                    delta = new_qty - old_qty
                    product.inventory.stock_qty = new_qty
                    db.session.add(
                        StockMovement(
                            product_id=product.id,
                            change_qty=delta,
                            reason=StockMovementReason.ADJUSTMENT,
                            note="Manual stock adjustment via product edit form.",
                        )
                    )

            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Something went wrong updating the product. Please try again.", "danger")
            return render_template("admin/product_form.html", form=form, mode="edit", product=product)

        flash(f"Product '{product.name}' updated.", "success")
        return redirect(url_for("admin.list_products"))

    return render_template("admin/product_form.html", form=form, mode="edit", product=product)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    try:
        name = product.name
        db.session.delete(product)  # cascades to Inventory + StockMovement rows
        db.session.commit()
        flash(f"Product '{name}' deleted.", "success")
    except Exception:
        db.session.rollback()
        flash(
            "Could not delete this product — it likely has existing orders referencing it.",
            "danger",
        )

    return redirect(url_for("admin.list_products"))
