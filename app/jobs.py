import traceback
from datetime import datetime

# import celery
from celery import Celery
from flask import (current_app, render_template)
from psycopg2 import OperationalError
from sqlalchemy.exc import SQLAlchemyError

from app import calendar, db, store
from app.constants import OPENRECORDS_DL_EMAIL, request_status
from app.constants.event_type import EMAIL_NOTIFICATION_SENT, REQ_STATUS_CHANGED
from app.constants.response_privacy import PRIVATE
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import send_email
from app.models import Agencies, Emails, Events, Requests, Users

# NOTE: (For Future Reference)
# If we find ourselves in need of a request context, app.test_request_context() might come in handy.

STATUSES_EMAIL_SUBJECT = "Nightly Request Status Report"
STATUSES_EMAIL_TEMPLATE = "email_templates/email_request_status_changed"

app = Celery()


@app.task(autoretry_for=(OperationalError, SQLAlchemyError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_request_statuses():
    try:
        _update_request_statuses()
    except Exception:
        db.session.rollback()
        send_email(
            subject="Update Request Statuses Failure",
            to=[OPENRECORDS_DL_EMAIL],
            email_content=traceback.format_exc().replace("\n", "<br/>").replace(" ", "&nbsp;")
        )


def _update_request_statuses():
    """
    Update statuses for all requests that are now Due Soon or Overdue
    and send a notification email to agency admins listing the requests.
    """
    now = datetime.utcnow()
    due_soon_date = calendar.addbusdays(
        now, current_app.config['DUE_SOON_DAYS_THRESHOLD']
    ).replace(hour=23, minute=59, second=59)  # the entire day

    agencies = Agencies.query.with_entities(Agencies.ein).filter_by(is_active=True).all()
    for agency_ein, in agencies:
        requests_overdue = Requests.query.filter(
            Requests.due_date < now,
            Requests.status != request_status.CLOSED,
            Requests.agency_ein == agency_ein
        ).order_by(
            Requests.due_date.asc()
        ).all()

        requests_due_soon = Requests.query.filter(
            Requests.due_date > now,
            Requests.due_date <= due_soon_date,
            Requests.status != request_status.CLOSED,
            Requests.agency_ein == agency_ein
        ).order_by(
            Requests.due_date.asc()
        ).all()

        if not requests_overdue and not requests_due_soon:
            continue

        agency_requests_overdue = []
        agency_acknowledgments_overdue = []
        agency_requests_due_soon = []
        agency_acknowledgments_due_soon = []

        # OVERDUE
        for request in requests_overdue:

            if request.was_acknowledged:
                agency_requests_overdue.append(request)
            else:
                agency_acknowledgments_overdue.append(request)

            if request.status != request_status.OVERDUE:
                create_object(
                    Events(
                        request.id,
                        user_guid=None,
                        type_=REQ_STATUS_CHANGED,
                        previous_value={"status": request.status},
                        new_value={"status": request_status.OVERDUE},
                        response_id=None,
                    )
                )
                update_object(
                    {"status": request_status.OVERDUE},
                    Requests,
                    request.id)

        # DUE SOON
        for request in requests_due_soon:

            if request.was_acknowledged:
                agency_requests_due_soon.append(request)
            else:
                agency_acknowledgments_due_soon.append(request)

            if request.status != request_status.DUE_SOON:
                create_object(
                    Events(
                        request.id,
                        user_guid=None,
                        type_=REQ_STATUS_CHANGED,
                        previous_value={"status": request.status},
                        new_value={"status": request_status.DUE_SOON},
                        response_id=None,
                    )
                )
                update_object(
                    {"status": request_status.DUE_SOON},
                    Requests,
                    request.id)

        # mail to agency admins for each agency
        user_emails = list(set(admin.notification_email or admin.email for admin
                               in Agencies.query.filter_by(ein=agency_ein).one().administrators))

        send_email(
            STATUSES_EMAIL_SUBJECT,
            to=user_emails,
            template=STATUSES_EMAIL_TEMPLATE,
            requests_overdue=agency_requests_overdue,
            acknowledgments_overdue=agency_acknowledgments_overdue,
            requests_due_soon=agency_requests_due_soon,
            acknowledgments_due_soon=agency_acknowledgments_due_soon
        )
        email = Emails(
            request.id,
            PRIVATE,
            to=','.join(user_emails),
            cc=None,
            bcc=None,
            subject=STATUSES_EMAIL_SUBJECT,
            body=render_template(
                STATUSES_EMAIL_TEMPLATE + ".html",
                requests_overdue=agency_requests_overdue,
                acknowledgments_overdue=agency_acknowledgments_overdue,
                requests_due_soon=agency_requests_due_soon,
                acknowledgments_due_soon=agency_acknowledgments_due_soon
            )
        )
        create_object(email)
        create_object(
            Events(
                request.id,
                user_guid=None,
                type_=EMAIL_NOTIFICATION_SENT,
                previous_value=None,
                new_value=email.val_for_events,
                response_id=None,
                timestamp=datetime.utcnow()
            )
        )


@app.task(autoretry_for=(OperationalError, SQLAlchemyError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_next_request_number():
    """
    Celery task to automatically update the next request number of each agency to 1
    :return:
    """
    try:
        for agency in Agencies.query.all():
            agency.next_request_number = 1
            db.session.add(agency)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


@app.task(autoretry_for=(OperationalError, SQLAlchemyError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def clear_expired_session_ids():
    """
    Celery task to clear session ids that are no longer valid.
    :return:
    """
    users = Users.query.with_entities(Users.guid, Users.session_id).filter(Users.session_id.isnot(None)).all()
    if users:
        for user in users:
            if store.get("session:" + user[1]) is None:
                update_object(
                    {
                        'session_id': None
                    },
                    Users,
                    user[0]
                )
