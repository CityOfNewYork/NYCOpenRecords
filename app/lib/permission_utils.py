from functools import wraps

from flask import abort, request, redirect
from flask_login import current_user, login_url
from sqlalchemy.orm.exc import NoResultFound
from app import login_manager, sentry
from app.constants import permission
from app.models import (
    Users,
    Responses,
    Files,
    Notes,
    Letters,
    Links,
    Instructions,
    Determinations,
    Envelopes
)


def has_permission(permission: int):
    """
    Checks to see if the current_user has the appropriate permission for this endpoint.

    :param f: View function that is being wrapped.
    :param permissions: List of permission values.
    :return:
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(request_id, *args, **kwargs):
            if not current_user.is_authenticated or current_user.is_anonymous:
                return redirect(login_url(login_manager.login_view,
                                          next_url=request.url))
            return f(request_id) if is_allowed(user=current_user, request_id=request_id,
                                               permission=permission) else abort(403)

        return decorated_function

    return decorator


def has_super():
    """
    Checks to see if the current_user is a super user.

    :param f: Function that is being wrapped.
    :return:
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not getattr(current_user, 'is_super', False):
                return abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def is_allowed(user: Users, request_id: str, permission: int):
    """

    :param user:
    :param request_id:
    :param permissions:
    :return:
    """
    try:
        user_request = user.user_requests.filter_by(request_id=request_id).one()
        return True if user_request.has_permission(permission) else False

    except NoResultFound:
        sentry.captureException()
        return False

    except AttributeError:
        sentry.captureException()
        return False


def get_permission(permission_type: str, response_type: Responses):
    """

    :param permission_type:
    :param response_type:
    :return:
    """

    if response_type not in [Determinations, Envelopes, Letters]:

        if permission_type == 'edit':
            permission_for_edit_type = {
                Files: permission.EDIT_FILE,
                Notes: permission.EDIT_NOTE,
                Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS,
                Links: permission.EDIT_LINK,
            }
            return permission_for_edit_type[response_type]

        if permission_type == 'privacy':
            permission_for_edit_type_privacy = {
                Files: permission.EDIT_FILE_PRIVACY,
                Notes: permission.EDIT_NOTE_PRIVACY,
                Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY,
                Links: permission.EDIT_LINK_PRIVACY
            }
            return permission_for_edit_type_privacy[response_type]

        if permission_type == 'delete':
            permission_for_delete_type = {
                Files: permission.DELETE_FILE,
                Notes: permission.DELETE_NOTE,
                Instructions: permission.DELETE_OFFLINE_INSTRUCTIONS,
                Links: permission.DELETE_LINK
            }
            return permission_for_delete_type[response_type]

    return 0
