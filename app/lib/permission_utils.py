from functools import wraps

from flask import (
    abort
)
from flask_login import current_user

from app.constants import permission
from app.models import (
    Users,
    Responses,
    Files,
    Notes,
    Links,
    Instructions
)


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
    return True


def get_permission(permission_type: str, response_type: Responses):
    """

    :param permission_type:
    :param response_type:
    :return:
    """
    if permission_type == 'edit':
        permission_for_edit_type = {
            Files: permission.EDIT_FILE,
            Notes: permission.EDIT_NOTE,
            Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS,
            Links: permission.EDIT_LINK
        }
        return [permission_for_edit_type[type(response_type)]]

    if permission_type == 'privacy':
        permission_for_edit_type_privacy = {
            Files: permission.EDIT_FILE,
            Notes: permission.EDIT_NOTE,
            Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS,
            Links: permission.EDIT_LINK
        }
        return [permission_for_edit_type_privacy[type(response_type)]]

    if permission_type == 'delete':
        permission_for_delete_type = {
            Files: permission.DELETE_FILE,
            Notes: permission.DELETE_NOTE,
            Instructions: permission.DELETE_OFFLINE_INSTRUCTIONS,
            Links: permission.DELETE_LINK
        }
        return [permission_for_delete_type[type(response_type)]]

    return None
