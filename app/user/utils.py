from datetime import datetime

from elasticsearch.helpers import bulk
from flask import current_app
from psycopg2 import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import (
    celery,
    db,
    es
)
from app.constants import (bulk_updates, event_type, role_name, user_type_request)
from app.lib.email_utils import (
    get_agency_admin_emails,
    send_email,
)
from app.models import (Agencies, Events, Requests, Roles, UserRequests, Users)


@celery.task(bind=True, name='app.user.utils.make_user_admin', autoretry_for=(OperationalError, SQLAlchemyError,),
             retry_kwargs={'max_retries': 5}, retry_backoff=True)
def make_user_admin(self, modified_user_guid: str, current_user_guid: str, agency_ein: str):
    """
    Make the specified user an admin for the agency.

    Args:
        modified_user_guid (str): GUID of the user to be modified
        current_user_guid (str): GUID of the current user
        agency_ein (str): Agency the user is being added to

    Returns:

    """
    permissions = Roles.query.filter_by(name=role_name.AGENCY_ADMIN).one().permissions
    user = Users.query.filter_by(guid=modified_user_guid).one()
    requests = [request.id for request in user.agencies.filter_by(ein=agency_ein).one().requests]

    new_user_requests = []
    new_user_requests_events = []

    update_user_requests = []
    update_user_requests_events = []

    for request in requests:
        existing_value = UserRequests.query.filter_by(request_id=request, user_guid=user.guid).one_or_none()

        if existing_value and existing_value.permissions != permissions:
            user_request = bulk_updates.UserRequestsDict(
                user_guid=user.guid,
                request_id=request,
                request_user_type=user_type_request.AGENCY,
                permissions=permissions,
                point_of_contact=existing_value.point_of_contact
            )
            update_user_requests.append(user_request)
            previous_value = {
                'user_guid': modified_user_guid,
                'permissions': existing_value.permissions
            }
            new_value = {
                'user_guid': modified_user_guid,
                'permissions': permissions
            }
            user_request_event = bulk_updates.UserRequestsEventDict(
                request_id=request,
                user_guid=user.guid,
                response_id=None,
                type=event_type.USER_PERM_CHANGED,
                timestamp=datetime.utcnow(),
                previous_value=previous_value,
                new_value=new_value,
            )
            update_user_requests_events.append(user_request_event)

        elif existing_value is None:
            user_request = bulk_updates.UserRequestsDict(
                user_guid=user.guid,
                request_id=request,
                request_user_type=user_type_request.AGENCY,
                permissions=permissions,
                point_of_contact=None
            )
            new_user_requests.append(user_request)

            new_value = {
                'user_guid': user.guid,
                'request_id': request,
                'request_user_type': user_type_request.AGENCY,
                'permissions': permissions,
                'point_of_contact': None
            }
            user_request_event = bulk_updates.UserRequestsEventDict(
                request_id=request,
                user_guid=current_user_guid,
                response_id=None,
                type=event_type.USER_ADDED,
                timestamp=datetime.utcnow(),
                previous_value=None,
                new_value=new_value
            )
            new_user_requests_events.append(user_request_event)
    try:
        UserRequests.query.filter(UserRequests.user_guid == user.guid).update([('permissions', permissions)])

        db.session.bulk_insert_mappings(Events, update_user_requests_events)
        db.session.bulk_insert_mappings(UserRequests, new_user_requests)
        db.session.bulk_insert_mappings(Events, new_user_requests_events)
        db.session.commit()

        agency = Agencies.query.filter_by(ein=agency_ein).one()

        admin_users = get_agency_admin_emails(agency)

        es_update_assigned_users.apply_async(args=[requests])

        send_email(
            subject='User {name} Made Admin'.format(name=user.name),
            to=admin_users,
            template='email_templates/email_user_made_agency_admin',
            agency_name=agency.name,
            name=user.name
        )

    except SQLAlchemyError:
        db.session.rollback()


@celery.task(bind=True, name='app.user.utils.remove_user_permissions',
             autoretry_for=(OperationalError, SQLAlchemyError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def remove_user_permissions(self, modified_user_guid: str, current_user_guid: str, agency_ein: str, action: str = None):
    """
    Remove the specified users permissions for the agency identified by agency_ein

    Args:
        modified_user_guid (str): GUID of the user to be modified
        current_user_guid (str): GUID of the current user
        agency_ein (str): Agency the user is being removed from

    Returns:

    """
    user_requests = db.session.query(UserRequests, Requests).join(Requests).with_entities(
        UserRequests.request_id, UserRequests.permissions, UserRequests.point_of_contact).filter(
        Requests.agency_ein == agency_ein, UserRequests.user_guid == modified_user_guid).all()
    request_ids = [ur.request_id for ur in user_requests]
    user = Users.query.filter_by(guid=modified_user_guid).one()

    remove_user_request_events = [bulk_updates.UserRequestsEventDict(
        request_id=ur.request_id,
        user_guid=current_user_guid,
        response_id=None,
        type=event_type.USER_REMOVED,
        timestamp=datetime.utcnow(),
        previous_value={
            'user_guid': modified_user_guid,
            'permissions': ur.permissions,
            'point_of_contact': ur.point_of_contact
        },
        new_value={
            'user_guid': modified_user_guid,
            'point_of_contact': False
        }
    ) for ur in user_requests]

    try:
        db.session.query(UserRequests).filter(UserRequests.user_guid == modified_user_guid,
                                              UserRequests.request_id.in_(request_ids)).delete(
            synchronize_session=False)
        db.session.bulk_insert_mappings(Events, remove_user_request_events)
        db.session.commit()

        es_update_assigned_users.apply_async(args=[request_ids])

        agency = Agencies.query.filter_by(ein=agency_ein).one()
        admin_users = get_agency_admin_emails(agency)

        if action == event_type.AGENCY_USER_DEACTIVATED:
            send_email(
                subject='User {name} Deactivated'.format(name=user.name),
                to=admin_users,
                template='email_templates/email_agency_user_deactivated',
                agency_name=agency.name,
                name=user.name
            )
        elif action == event_type.USER_MADE_AGENCY_USER:
            send_email(
                subject='User {name} Made Regular User'.format(name=user.name),
                to=admin_users,
                template='email_templates/email_user_removed_agency_admin',
                agency_name=agency.name,
                name=user.name
            )

    except SQLAlchemyError:
        db.session.rollback()


@celery.task(bind=True, name='app.user.utils.es_update_assigned_users',
             autoretry_for=(OperationalError, SQLAlchemyError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def es_update_assigned_users(self, request_ids: list):
    """
    Update the ElasticSearch index assigned_users for the provided request IDs.

    Args:
        request_ids (list): List of Request IDs
    """
    try:
        actions = [{
            '_op_type': 'update',
            '_id': request.id,
            'doc': {
                'assigned_users': [user.get_id() for user in request.agency_users]
            }
        } for request in
            Requests.query.filter(Requests.id.in_(request_ids)).options(joinedload(Requests.agency_users)).all()]
    except SQLAlchemyError:
        db.session.rollback()

    bulk(
        es,
        actions,
        index=current_app.config['ELASTICSEARCH_INDEX'],
        chunk_size=current_app.config['ELASTICSEARCH_CHUNK_SIZE']
    )
