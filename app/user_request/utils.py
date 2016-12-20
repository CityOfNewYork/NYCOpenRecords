from urllib.parse import urljoin
from flask import (
    request as flask_request,
    render_template,
    url_for
)
from app.response.utils import (
    safely_send_and_add_email,
    create_response_event
)
from app.lib.db_utils import delete_object, create_object
from app.models import (
    Users,
    UserRequests,
    Requests,
)
from app.lib.utils import UserRequestException
from app.constants import event_type, permission, user_type_request


def add_user_request(request_id, user_guid, permissions):
    """
    Create a users permissions entry for a request and notify all agency administrators and the user that the permissions
    have changed.

    :param request_id: FOIL request ID
    :param user_guid: string guid of the user being edited
    :param permissions: Updated permissions values {'permission': true}
    """
    user_request = UserRequests.query.filter_by(user_guid=user_guid,
                                                request_id=request_id).first()

    if user_request:
        raise UserRequestException(action="create", request_id=request_id, reason="UserRequest entry already exists.")

    user = Users.query.filter_by(guid=user_guid).one()

    agency_admin_emails = _get_agency_admin_emails(request_id)

    added_permissions = []
    for i, val in enumerate(permission.ALL):
        if i in permissions:
            added_permissions.append(val)

    # send email to agency administrators
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_added.html',
            request_id=request_id,
            name=user.name,
            agency_name=user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            admin=True),
        'User Removed from Request',
        to=agency_admin_emails)

    # send email to user being removed
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_added.html',
            request_id=request_id,
            name=user.name,
            agency_name=user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
        ),
        'User Removed from Request',
        to=[user.email])

    user_request = UserRequests(
        user_guid=user.guid,
        auth_user_type=user.auth_user_type,
        request_id=request_id,
        request_user_type=user_type_request.AGENCY,
        permissions=0
    )

    create_object(user_request)

    if added_permissions:
        user_request.add_permissions([capability.value for capability in added_permissions])

    create_response_event(event_type.USER_ADDED, user_request=user_request)


def edit_user_request(request_id, user_guid, permissions):
    """
    Edit a users permissions on a request and notify all agency administrators and the user that the permissions
    have changed.

    :param request_id: FOIL request ID
    :param user_guid: string guid of the user being edited
    :param permissions: Updated permissions values {'permission': true}
    """
    user_request = UserRequests.query.filter_by(user_guid=user_guid,
                                                request_id=request_id).one()

    agency_admin_emails = _get_agency_admin_emails(request_id)

    added_permissions = []
    removed_permissions = []
    for i, val in enumerate(permission.ALL):
        if i in permissions:
            added_permissions.append(val)
        else:
            removed_permissions.append(val)

    # send email to agency administrators
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_edited.html',
            request_id=request_id,
            name=user_request.user.name,
            agency_name=user_request.user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            removed_permissions=[capability.label for capability in removed_permissions],
            admin=True),
        'User Removed from Request',
        to=agency_admin_emails)

    # send email to user being removed
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_edited.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=user_request.user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            removed_permissions=[capability.label for capability in removed_permissions],
        ),
        'User Removed from Request',
        to=[user_request.user.email])

    if added_permissions:
        user_request.add_permissions([capability.value for capability in added_permissions])
    if removed_permissions:
        user_request.remove_permissions([capability.value for capability in removed_permissions])

    create_response_event(event_type.USER_PERM_CHANGED, user_request=user_request)


def remove_user_request(request_id, user_guid):
    """
    Remove user from request and sends email to all agency administrators and to user being removed.
    Delete row from UserRequests table and stores event object into Events.

    :param request_id: FOIL request ID
    :param user_guid: string guid of user being removed

    """
    user_request = UserRequests.query.filter_by(user_guid=user_guid,
                                                request_id=request_id).first()
    agency_admin_emails = _get_agency_admin_emails(request_id)

    # send email to agency administrators
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_removed.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=user_request.user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            admin=True),
        'User Removed from Request',
        to=agency_admin_emails)

    # send email to user being removed
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_removed.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=user_request.user.agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id))),
        'User Removed from Request',
        to=[user_request.user.email])

    create_response_event(event_type.USER_REMOVED, user_request=user_request)
    delete_object(user_request)


def _get_agency_admin_emails(request_id):
    """
    Retrieve a list of agency administrator emails
    :param request_id: FOIL request id
    :return: list(Agency Adminstrator Emails)
    """

    agency_ein = Requests.query.filter_by(id=request_id).one().agency.ein

    agency_administrators = Users.query.filter_by(agency_ein=agency_ein,
                                                  is_agency_admin=True,
                                                  is_agency_active=True
                                                  ).all()

    return [user.email for user in agency_administrators]
