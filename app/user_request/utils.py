from datetime import datetime
from sqlalchemy.orm import joinedload
from urllib.parse import urljoin

from flask import (
    request as flask_request,
    render_template,
    url_for
)
from flask_login import current_user

from app.constants import event_type, permission, user_type_request
from app.lib.db_utils import delete_object, create_object, update_object
from app.lib.email_utils import get_agency_admin_emails
from app.lib.utils import UserRequestException
from app.models import (
    Users,
    UserRequests,
    Requests,
    Events,
)
from app.response.utils import safely_send_and_add_email


def add_user_request(request_id, user_guid, permissions, point_of_contact):
    """
    Create a users permissions entry for a request and notify all agency administrators and the user that the permissions
    have changed.

    :param request_id: FOIL request ID
    :param user_guid: string guid of the user being edited
    :param permissions: Updated permissions values {'permission': true}
    :param point_of_contact: boolean value to set user as point of contact or not
    """
    user_request = UserRequests.query.filter_by(user_guid=user_guid,
                                                request_id=request_id).first()

    agency = Requests.query.filter_by(id=request_id).one().agency

    if user_request:
        raise UserRequestException(action="create", request_id=request_id, reason="UserRequest entry already exists.")

    user = Users.query.filter_by(guid=user_guid).one()

    agency_admin_emails = get_agency_admin_emails(agency)

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
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            admin=True),
        'User Added to Request {}'.format(request_id),
        to=agency_admin_emails)

    # send email to user being added
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_added.html',
            request_id=request_id,
            name=user.name,
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
        ),
        'User Added to Request {}'.format(request_id),
        to=[user.notification_email or user.email])

    if point_of_contact and has_point_of_contact(request_id):
        remove_point_of_contact(request_id)
    user_request = UserRequests(
        user_guid=user.guid,
        request_id=request_id,
        request_user_type=user_type_request.AGENCY,
        permissions=0,
        point_of_contact=point_of_contact
    )

    create_object(user_request)

    if added_permissions:
        user_request.add_permissions([capability.value for capability in added_permissions])

    user_request.request.es_update()

    create_user_request_event(event_type.USER_ADDED, user_request)


def edit_user_request(request_id, user_guid, permissions, point_of_contact):
    """
    Edit a users permissions on a request and notify all agency administrators and the user that the permissions
    have changed.

    :param request_id: FOIL request ID
    :param user_guid: string guid of the user being edited
    :param permissions: Updated permissions values {'permission': true}
    :param point_of_contact: boolean value to set user as point of contact or not
    """
    user_request = UserRequests.query.options(
        joinedload(UserRequests.user)
    ).filter_by(
        user_guid=user_guid,
        request_id=request_id
    ).one()

    agency = Requests.query.filter_by(id=request_id).one().agency
    agency_admin_emails = get_agency_admin_emails(agency)

    added_permissions = []
    removed_permissions = []
    for i, val in enumerate(permission.ALL):
        if i in permissions:
            added_permissions.append(val)
        else:
            removed_permissions.append(val)

    # send email to agency administrators
    tmp = safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_edited.html',
            request_id=request_id,
            name=user_request.user.name,
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            removed_permissions=[capability.label for capability in removed_permissions],
            admin=True),
        'User Permissions Edited for Request {}'.format(request_id),
        to=agency_admin_emails)

    # send email to user being edited
    tmp = safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_edited.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            added_permissions=[capability.label for capability in added_permissions],
            removed_permissions=[capability.label for capability in removed_permissions],
        ),
        'User Permissions Edited for Request {}'.format(request_id),
        to=[user_request.user.notification_email or user_request.user.email])

    old_permissions = user_request.permissions
    old_point_of_contact = user_request.point_of_contact

    if added_permissions:
        user_request.add_permissions([capability.value for capability in added_permissions])
    if removed_permissions:
        user_request.remove_permissions([capability.value for capability in removed_permissions])

    determine_point_of_contact_change(request_id, user_request, point_of_contact)
    create_user_request_event(event_type.USER_PERM_CHANGED, user_request, old_permissions, old_point_of_contact)


def remove_user_request(request_id, user_guid):
    """
    Remove user from request and sends email to all agency administrators and to user being removed.
    Delete row from UserRequests table and stores event object into Events.

    :param request_id: FOIL request ID
    :param user_guid: string guid of user being removed

    """
    user_request = UserRequests.query.options(
        joinedload(UserRequests.user)
    ).filter_by(
        user_guid=user_guid, request_id=request_id
    ).one()
    request = Requests.query.filter_by(id=request_id).one()
    agency = request.agency
    agency_admin_emails = get_agency_admin_emails(agency)

    # send email to agency administrators
    tmp = safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_removed.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id)),
            admin=True),
        'User Removed from Request {}'.format(request_id),
        to=agency_admin_emails)

    # send email to user being removed
    tmp = safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_user_request_removed.html',
            request_id=request_id,
            name=' '.join([user_request.user.first_name, user_request.user.last_name]),
            agency_name=agency.name,
            page=urljoin(flask_request.host_url, url_for('request.view', request_id=request_id))),
        'User Removed from Request {}'.format(request_id),
        to=[user_request.user.email])
    old_permissions = user_request.permissions
    old_point_of_contact = user_request.point_of_contact

    create_user_request_event(event_type.USER_REMOVED, user_request, old_permissions, old_point_of_contact)
    delete_object(user_request)

    request.es_update()


def create_user_request_event(events_type, user_request, old_permissions=None, old_point_of_contact=None,
                              user=current_user):
    """
    Create an Event for the addition, removal, or updating of a UserRequest and insert into the database.

    Args:
        events_type (str): event type from the constants defined in constants.event_type.
        user_request (UserRequests): UserRequests object.
        old_permissions (int): Value of permissions for the request.
        user (Users): Users object that represents the user being modified.

    Returns:
        Events: The event object representing the change made to the user.

    """
    event = create_user_request_event_object(events_type, user_request, old_permissions, old_point_of_contact, user)
    create_object(
        event
    )


def create_user_request_event_object(events_type, user_request, old_permissions=None, old_point_of_contact=None,
                                     user=current_user):
    """
    Create an Event for the addition, removal, or updating of a UserRequest and insert into the database.

    Args:
        events_type (str): event type from the constants defined in constants.event_type.
        user_request (UserRequests): UserRequests object.
        old_permissions (int): Value of permissions for the request.
        user (Users): Users object that represents the user performing the user_request modification

    Returns:
        Events: The event object representing the change made to the user.

    """

    previous_value = {'user_guid': user_request.user_guid}
    if old_permissions is not None:
        previous_value['permissions'] = old_permissions

    if old_point_of_contact is not None:
        previous_value['point_of_contact'] = old_point_of_contact

    return Events(
        user_request.request_id,
        user.guid,
        events_type,
        previous_value=previous_value,
        new_value=user_request.val_for_events,
        timestamp=datetime.utcnow(),
    )


def get_current_point_of_contact(request_id):
    """
    Get the current point of contact of a given request
    :param request_id: FOIL request ID
    :return: UserRequest object of the current point of contact
    """
    return UserRequests.query.filter_by(request_id=request_id, point_of_contact=True).one_or_none()


def set_point_of_contact(request_id, user_request, point_of_contact):
    """
    Toggles point of contact of a given request
    :param request_id: FOIL request ID
    :param user_request: UserRequest row to be changed
    :param point_of_contact: boolean flag for point of contact
    """
    update_object({"point_of_contact": point_of_contact},
                  UserRequests,
                  (user_request.user_guid, request_id)
                  )


def has_point_of_contact(request_id):
    """
    Check if a given request has a point of contact
    :param request_id: FOIL request ID
    :return: True if there is a current point of contact, False otherwise
    """
    if get_current_point_of_contact(request_id):
        return True
    return False


def remove_point_of_contact(request_id):
    """
    Remove the current point of contact from a given request
    :param request_id: FOIL request ID
    """
    point_of_contact = get_current_point_of_contact(request_id)
    set_point_of_contact(request_id, point_of_contact, False)
    create_object(Events(
        request_id,
        current_user.guid,
        event_type.REQ_POINT_OF_CONTACT_REMOVED,
        previous_value={"user_guid": point_of_contact.user_guid,
                        "point_of_contact": "True"},
        new_value={"user_guid": point_of_contact.user_guid,
                   "point_of_contact": "False"},
        timestamp=datetime.utcnow(),
    ))


def determine_point_of_contact_change(request_id, user_request, point_of_contact):
    """
    Determines what action needs to be done to the point of contact
    :param request_id: FOIL request ID
    :param user_request: UserRequest row to be changed
    :param point_of_contact: boolean flag for point of contact
    """
    current_point_of_contact = get_current_point_of_contact(request_id)
    if current_point_of_contact is not None and user_request.user_guid == current_point_of_contact.user_guid and point_of_contact != current_point_of_contact.point_of_contact:
        # toggle the flag of the current point of contact
        if not point_of_contact:
            remove_point_of_contact(request_id)
        else:
            set_point_of_contact(request_id, current_point_of_contact, point_of_contact)
    elif current_point_of_contact is None and point_of_contact:
        # set a brand new point of contact
        set_point_of_contact(request_id, user_request, True)
    elif has_point_of_contact(
            request_id) and current_point_of_contact.user_guid != user_request.user_guid and point_of_contact:
        # replace the previous point of contact
        remove_point_of_contact(request_id)
        set_point_of_contact(request_id, user_request, point_of_contact)
