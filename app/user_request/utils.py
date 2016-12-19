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
from app.lib.db_utils import delete_object
from app.models import (
    Users,
    UserRequests,
    Requests,
)
from app.constants import event_type


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

    for key, val in enumerate(permissions):
        if permission






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
            'email_templates/email_removed_user_request.html',
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
            'email_templates/email_removed_user_request.html',
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

    agency_ein = Requests.query.filter_by(request_id=request_id).one().agency.agency_ein

    agency_administrators = Users.query.filter_by(agency_ein=agency_ein, is_agency_admin=True).all()

    return [user.email for user in agency_administrators]
