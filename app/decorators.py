"""
Shared view decorators.
"""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view_func):
    """
    Combines @login_required with an admin-role check.
    Returns 403 for logged-in non-admins (as opposed to redirecting to
    login, which would be misleading since they ARE logged in).
    """

    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped
