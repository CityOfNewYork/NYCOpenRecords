from functools import wraps

from flask import (
    abort
)
from flask_login import current_user

from app.models import Users


def has_permission(permissions: list):
    """
    Checks to see if the current_user has the appropriate permission for this endpoint.

    :param f: View function that is being wrapped.
    :param permissions: List of permission values.
    :return:
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(request_id):
            if current_user.is_anonymous:
                return abort(403)
            return f(request_id) if not permission_checker(user=current_user, request_id=request_id,
                                                           permissions=permissions) else abort(403)

        return decorated_function

    return decorator


def permission_checker(user: Users, request_id: str, permissions: list):
    """

    :param user:
    :param request_id:
    :param permissions:
    :return:
    """
    user_request = user.user_requests.filter_by(request_id=request_id).one()
    for permission in permissions:
        if not user_request.has_permission(permission):
            return False
