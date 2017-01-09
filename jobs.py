from datetime import datetime
from urllib.parse import urljoin

from flask import (
    render_template,
    current_app,
    url_for,
)
from app import calendar, scheduler
from app.models import Requests, Events, Emails
from app.constants import request_status
from app.constants.event_type import EMAIL_NOTIFICATION_SENT
from app.constants.response_privacy import PRIVATE
from app.lib.db_utils import update_object, create_object
from app.lib.email_utils import send_email

# NOTE: (For Future Reference)
# If we find ourselves in need of a request context,
# app.test_request_context() is an option.


def update_request_statuses():
    with scheduler.app.app_context():
        now = datetime.utcnow()
        due_soon_date = calendar.addbusdays(
            now, current_app.config['DUE_SOON_DAYS_THRESHOLD']
        ).replace(hour=23, minute=59, second=59)  # the entire day

        requests_overdue = Requests.query.filter(
            Requests.due_date < now).all()

        requests_due_soon = Requests.query.filter(
            Requests.due_date > now,
            Requests.due_date <= due_soon_date).all()

        template = "email_templates/email_request_status_changed"

        for request in requests_overdue:
            page = url_for('request.view', request_id=request.id)
            subject = "Request Overdue"
            if request.status != request_status.OVERDUE:
                update_object(
                    {"status": request_status.OVERDUE},
                    Requests,
                    request.id)
            user_emails = [u.email for u in request.agency_users]
            send_email(
                subject,
                to=user_emails,
                template=template,
                request=request,
                request_status=request_status,
                agency_name=request.agency.name,
                page=page,
            )
            email = Emails(
                request.id,
                PRIVATE,
                to=','.join(user_emails),
                cc=None,
                bcc=None,
                subject=subject,
                body=render_template(
                    template + ".html",
                    request=request,
                    request_status=request_status,
                    agency_name=request.agency.name,
                    page=page,
                )
            )
            create_object(email)
            create_object(
                Events(
                    request.id,
                    user_guid=None,
                    auth_user_type=None,
                    type_=EMAIL_NOTIFICATION_SENT,
                    previous_value=None,
                    new_value=email.val_for_events,
                    response_id=None,
                    timestamp=datetime.utcnow()
                )
            )

        for request in requests_due_soon:
            page = url_for('request.view', request_id=request.id)
            subject = "Requests Due Soon"
            timedelta_until_due = request.due_date - now
            if request.status != request_status.DUE_SOON:
                update_object(
                    {"status": request_status.DUE_SOON},
                    Requests,
                    request.id)
            user_emails = [u.email for u in request.agency_users]
            send_email(
                subject,
                to=user_emails,
                template=template,
                request=request,
                request_status=request_status,
                days_until_due=timedelta_until_due.days,
                agency_name=request.agency.name,
                page=page,
            )
            email = Emails(
                request.id,
                PRIVATE,
                to=','.join(user_emails),
                cc=None,
                bcc=None,
                subject=subject,
                body=render_template(
                    template + ".html",
                    request=request,
                    request_status=request_status,
                    days_until_due=timedelta_until_due.days,
                    agency_name=request.agency.name,
                    page=page,
                )
            )
            create_object(email)
            create_object(
                Events(
                    request.id,
                    user_guid=None,
                    auth_user_type=None,
                    type_=EMAIL_NOTIFICATION_SENT,
                    previous_value=None,
                    new_value=email.val_for_events,
                    response_id=None,
                    timestamp=datetime.utcnow()
                )
            )
