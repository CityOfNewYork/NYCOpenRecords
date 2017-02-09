from datetime import datetime
from urllib.parse import urljoin

from flask import (
    render_template,
    current_app,
)
from app import calendar, scheduler
from app.models import Requests, Events, Emails, Agencies
from app.constants import request_status
from app.constants.event_type import EMAIL_NOTIFICATION_SENT
from app.constants.response_privacy import PRIVATE
from app.lib.db_utils import update_object, create_object
from app.lib.email_utils import send_email


# NOTE: (For Future Reference)
# If we find ourselves in need of a request context,
# app.test_request_context() is an option.

STATUSES_EMAIL_SUBJECT = "Nightly Request Status Report"
STATUSES_EMAIL_TEMPLATE = "email_templates/email_request_status_changed"


def update_request_statuses():
    """
    Update statuses for all requests that are now Due Soon or Overdue
    and send a notification email to agency admins listing the requests.
    """
    with scheduler.app.app_context():
        now = datetime.utcnow()
        due_soon_date = calendar.addbusdays(
            now, current_app.config['DUE_SOON_DAYS_THRESHOLD']
        ).replace(hour=23, minute=59, second=59)  # the entire day

        requests_overdue = Requests.query.filter(
            Requests.due_date < now,
            Requests.status != request_status.CLOSED
        ).order_by(
            Requests.due_date.asc()
        ).all()

        requests_due_soon = Requests.query.filter(
            Requests.due_date > now,
            Requests.due_date <= due_soon_date,
            Requests.status != request_status.CLOSED
        ).order_by(
            Requests.due_date.asc()
        ).all()

        agencies_to_requests_overdue = {}
        agencies_to_acknowledgments_overdue = {}
        agencies_to_requests_due_soon = {}
        agencies_to_acknowledgments_due_soon = {}

        def add_to_agencies_to_request_dict(req, agencies_to_request_dict):
            if req.agency.ein not in agencies_to_request_dict:
                agencies_to_request_dict[req.agency.ein] = [req]
            else:
                agencies_to_request_dict[req.agency.ein].append(req)

        # OVERDUE
        for request in requests_overdue:

            if request.was_acknowledged:
                add_to_agencies_to_request_dict(request, agencies_to_requests_overdue)
            else:
                add_to_agencies_to_request_dict(request, agencies_to_acknowledgments_overdue)

            if request.status != request_status.OVERDUE:
                update_object(
                    {"status": request_status.OVERDUE},
                    Requests,
                    request.id)

        # DUE SOON
        for request in requests_due_soon:

            if request.was_acknowledged:
                add_to_agencies_to_request_dict(request, agencies_to_requests_due_soon)
            else:
                add_to_agencies_to_request_dict(request, agencies_to_acknowledgments_due_soon)

            if request.status != request_status.DUE_SOON:
                update_object(
                    {"status": request_status.DUE_SOON},
                    Requests,
                    request.id)

        # get all possible agencies to email
        agency_eins = set(
            list(agencies_to_requests_overdue) +
            list(agencies_to_acknowledgments_overdue) +
            list(agencies_to_requests_due_soon) +
            list(agencies_to_acknowledgments_due_soon))

        # mail to agency admins for each agency
        for agency_ein in agency_eins:
            agency_requests_overdue = agencies_to_requests_overdue.get(agency_ein, [])
            agency_acknowledgments_overdue = agencies_to_acknowledgments_overdue.get(agency_ein, [])
            agency_requests_due_soon = agencies_to_requests_due_soon.get(agency_ein, [])
            agency_acknowledgments_due_soon = agencies_to_acknowledgments_due_soon.get(agency_ein, [])

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
                    auth_user_type=None,
                    type_=EMAIL_NOTIFICATION_SENT,
                    previous_value=None,
                    new_value=email.val_for_events,
                    response_id=None,
                    timestamp=datetime.utcnow()
                )
            )
