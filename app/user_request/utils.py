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
    UserRequests
)
from app.constants import event_type


def remove_user_request(request_id, user_guid):
    """
    Remove user from request and sends email to all agency administrators and to user being removed.
    Delete row from UserRequests table and stores event object into Events.

    :param request_id: FOIL request ID
    :param user_guid: string guid of user being removed

    """
    user_request = UserRequests.query.filter_by(user_guid=user_guid,
                                                request_id=request_id).first()
    agency_admins = Users.query.filter_by(agency_ein=user_request.user.agency_ein,
                                          is_agency_admin=True).all()
    admin_emails = []
    for agency_admin in agency_admins:
        admin_emails.append(agency_admin.email)

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
        to=admin_emails)

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
