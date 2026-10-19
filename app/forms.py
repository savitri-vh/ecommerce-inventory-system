"""
Flask-WTF forms. Shared across blueprints; Phase 2+ forms (product, restock,
etc.) will be appended here as those phases are built.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class ProductForm(FlaskForm):
    """
    Used for both add and edit. `category_id` choices are populated at
    request time in the view (SelectField needs the live category list),
    and SKU uniqueness is checked in the view since it depends on whether
    we're editing the current row or creating a new one.
    """

    name = StringField("Product Name", validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    price = DecimalField(
        "Price", places=2, validators=[DataRequired(), NumberRange(min=0.01, message="Price must be greater than 0.")]
    )
    sku = StringField("SKU", validators=[DataRequired(), Length(min=2, max=64)])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    stock_qty = IntegerField(
        "Initial Stock Quantity",
        validators=[DataRequired(), NumberRange(min=0, message="Stock cannot be negative.")],
    )
    reorder_threshold = IntegerField(
        "Reorder Threshold",
        validators=[DataRequired(), NumberRange(min=0, message="Threshold cannot be negative.")],
    )
    submit = SubmitField("Save Product")
