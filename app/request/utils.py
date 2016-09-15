#!/usr/bin/python
# -*- coding: utf-8 -*-
# TODO: Module Level Comments
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

"""

from app.models import Request, Agency, Event
from app.db_utils import create_object, update_object
from datetime import datetime
from business_calendar import FOLLOWING
from app import calendar
from app.constants import ACKNOWLEDGEMENT_DAYS_DUE
from flask import render_template


def process_request(title=None, description=None, agency=None, submission=None):
    """

    :param title:
    :param description:
    :param agency:
    :param date_created:
    :param submission:
    :return:
    """
    # 1. Generate the request id
    request_id = generate_request_id()

    # 2a. Generate Email Notification Text for Agency
    agency_email = generate_email_template('agency_acknowledgment.html', request_id=request_id)
    # 2b. Generate Email Notification Text for Requester

    # 3a. Send Email Notification Text for Agency
    # 3b. Send Email Notification Text for Requester

    # 4a. Calculate Request Submitted Date (Round to next business day)
    date_created = datetime.now()
    date_submitted = get_date_submitted(date_created)

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = calc_due_date(date_submitted, ACKNOWLEDGEMENT_DAYS_DUE)

    # 5. Create File object (Response table if applicable)

    # 6. Store File object

    # 7. Create Request object
    req = Request(id=request_id, title=title, description=description, date_created=date_created,
                  date_submitted=date_submitted, due_date=due_date, submission=submission)
    # 8. Store Request object
    create_object(type="Request", obj=req)
    # 9. Store Events object
    event = Event(id=id, request_id=request_id, timestamp=datetime.utcnow())
    create_object(type="Event", obj=event)


def generate_request_id(agency):
    """

    :param agency:
    :return:
    """
    next_request_number = Agency.query.filter_by(ein=agency).first().next_request_number
    update_object(type="agency", field="next_request_number", value=next_request_number + 1)
    request_id = 'FOIL-{}-{}-{}'.format(datetime.now().strftime("%Y"), agency, next_request_number)
    return request_id


def generate_email_template(template_name, **kwargs):
    """

    :param template_name:
    :param kwargs:
    :return:
    """
    return render_template(template_name, **kwargs)


def get_date_submitted(date_created):
    """

    :param date_created:
    :return:
    """
    date_submitted = calendar.addbusdays(calendar.adjust(date_created, FOLLOWING), FOLLOWING)
    return date_submitted


def calc_due_date(date_submitted, days_until_due, hour_due=17, minute_due=00, second_due=00):
    """

    :param date_submitted:
    :param days_until_due:
    :param hour_due: Hour when the request will be marked as overdue, defaults to 1700 (5 P.M.)
    :param minute_due: Minute when the request will be marked as overdue, defaults to 00 (On the hour)
    :param second_due: Second when the request will be marked as overdue, defaults to 00
    :return:
    """
    due_date = calendar.addbusdays(calendar.adjust(date_submitted.replace(hour_due, minute_due, second_due),
                                                   days_until_due), days_until_due)
    return due_date

