from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission


def permission_required(permission):
    """
    Used to create custom decorators based on permissions to be used in conjunction with view functions.
    :param permission: The permission to check for.
    :return: Boolean (True if current user has current permission, False otherwise)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)  # 'Forbidden' HTTP Error
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """
    Decorator to be used in view functions. When this decorates a view function, only Administrators will have access
    to the page.
    :param f: Used so that decorator is operational.
    :return: Boolean (True if current user has the ADMINISTER permission, False otherwise)
    """
    return permission_required(Permission.ADMINISTER)(f)
