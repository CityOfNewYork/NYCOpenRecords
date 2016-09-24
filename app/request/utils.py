#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for requests

"""

import random
import string
import uuid
from datetime import datetime

from business_calendar import FOLLOWING
from flask import render_template
from flask_login import current_user

from app import calendar
from app.constants import (
    ACKNOWLEDGEMENT_DAYS_DUE,
    EVENT_TYPE,
    ANONYMOUS_USER
)
from app.db_utils import create_object, update_object
from app.models import Requests, Agencies, Events, Users, UserRequests, Roles


def create_request(title=None, description=None, agencies=None, submission='Direct Input', agency_date_submitted=None,
                   email=None, first_name=None, last_name=None, user_title=None, organization=None, phone=None,
                   fax=None, address=None):
    """
    Function for creating and storing a new request on the backend.

    :param title: request title
    :param description: detailed description of the request
    :param agency: agency selected for the request
    :param date_created: date the request was made
    :param submission: request submission method
    :return: creates and stores the request and event object for a new FOIL request
             Request and Event table are updated in the database
    """
    # 1. Generate the request id
    request_id = generate_request_id(agencies)

    # 2a. Generate Email Notification Text for Agency
    # agency_email = generate_email_template('agency_acknowledgment.html', request_id=request_id)
    # 2b. Generate Email Notification Text for Requester

    # 3a. Send Email Notification Text for Agency
    # 3b. Send Email Notification Text for Requester

    # 4a. Calculate Request Submitted Date (Round to next business day)
    date_created = datetime.now()
    date_submitted = get_date_submitted(date_created)

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = get_due_date(date_submitted, ACKNOWLEDGEMENT_DAYS_DUE)

    # 5. Create File object (Response table if applicable)

    # 6. Store File object

    # 7a. Create and store Request object for public user
    if current_user.is_public:
        request = Requests(id=request_id, title=title, agency=agencies, description=description,
                           date_created=date_created, date_submitted=date_submitted, due_date=due_date,
                           submission=submission)
        create_object(obj=request)

        # 9. Create Event object
        event = Events(user_id=current_user.guid, user_type=current_user.user_type, request_id=request_id,
                       type=EVENT_TYPE['request_created'], timestamp=datetime.utcnow())

        # 10. Store Event object
        create_object(obj=event)

        user_request_entry = UserRequests(user_guid=current_user.guid, user_type=current_user.user_type,
                                          request_id=request_id,
                                          permissions=Roles.query.filter_by(
                                              name='Public User - Requester').first().permissions)

        create_object(obj=user_request_entry)

    # 7b. Create and store Request and User object for anonymous user
    if current_user.is_anonymous:
        req = Requests(id=request_id, title=title, agency=agencies, description=description, date_created=date_created,
                       date_submitted=date_submitted, due_date=due_date, submission=submission)
        create_object(obj=req)
        guid = generate_guid()
        user = Users(guid=guid, user_type=ANONYMOUS_USER, email=email, first_name=first_name,
                     last_name=last_name, title=user_title, organization=organization, email_validated=False,
                     terms_of_use_accepted=False, phone_number=phone, fax_number=fax, mailing_address=address)
        create_object(obj=user)
        # 9. Create Event object
        event = Events(user_id=user.guid, user_type=user.user_type, request_id=request_id,
                       type=EVENT_TYPE['request_created'], timestamp=datetime.utcnow())

        # 10. Store Event object
        create_object(obj=event)

        user_request_entry = UserRequests(user_guid=user.guid, user_type=user.user_type, request_id=request_id,
                                          permissions=Roles.query.filter_by(name='Anonymous User').first().permissions)

        create_object(obj=user_request_entry)

    # 7c. Create and store Request and User object for agency user
    if current_user.is_agency:
        due_date = get_due_date(agency_date_submitted, ACKNOWLEDGEMENT_DAYS_DUE)
        request = Requests(id=request_id, title=title, agency=agencies, description=description,
                           date_created=date_created,
                           date_submitted=date_submitted, due_date=due_date, submission=submission)
        create_object(obj=request)
        guid = generate_guid()
        user = Users(guid=guid, user_type=ANONYMOUS_USER, email=email, first_name=first_name,
                     last_name=last_name, title=user_title, organization=organization, email_validated=False,
                     terms_of_use_accepted=False, phone_number=phone, fax_number=fax, mailing_address=address)
        create_object(obj=user)

        # 9. Create Event object
        event = Events(user_id=user.guid, user_type=user.user_type, request_id=request_id,
                       type=EVENT_TYPE['request_created'], timestamp=datetime.utcnow())

        # 10. Store Event object
        create_object(obj=event)

        user_request_entry = UserRequests(user_guid=user.guid, user_type=user.user_type, request_id=request_id,
                                          permissions=Roles.query.filter_by(
                                              name='Agency FOIL Officer').first().permissions)

        create_object(obj=user_request_entry)


def generate_request_id(agencies):
    """

    :param agency: agency ein used as a paramater to generate the request_id
    :return: generated FOIL Request ID (FOIL - year - agency ein - 5 digits for request number)
    """
    if agencies:
        next_request_number = Agencies.query.filter_by(ein=agencies).first().next_request_number
        update_object(attribute='next_request_number', value=next_request_number + 1, obj_type="Agencies",
                      obj_id=agencies)
        request_id = "FOIL-{0:s}-{1:03d}-{2:05d}".format(datetime.now().strftime("%Y"), int(agencies),
                                                         int(next_request_number))
        return request_id
    return None


def generate_email_template(template_name, **kwargs):
    """

    :param template_name: specific email template
    :param kwargs:
    :return: email template
    """
    return render_template(template_name, **kwargs)


def get_date_submitted(date_created):
    """
    Function that generates the date submitted for a request

    :param date_created: date the request was made
    :return: date submitted which is the date_created rounded off to the next business day
    """
    date_submitted = calendar.addbusdays(date_created, FOLLOWING)
    return date_submitted


def get_due_date(date_submitted, days_until_due, hour_due=17, minute_due=00, second_due=00):
    """
    Function that generates the due date for a request

    :param date_submitted: date submitted which is the date_created rounded off to the next business day
    :param days_until_due: number of business days until a request is due
    :param hour_due: Hour when the request will be marked as overdue, defaults to 1700 (5 P.M.)
    :param minute_due: Minute when the request will be marked as overdue, defaults to 00 (On the hour)
    :param second_due: Second when the request will be marked as overdue, defaults to 00
    :return: due date which is 5 business days after the date_submitted and time is always 5:00 PM
    """
    calc_due_date = calendar.addbusdays(date_submitted, days_until_due)  # calculates due date
    due_date = calc_due_date.replace(hour=hour_due, minute=minute_due, second=second_due)  # sets time to 5:00 PM
    return due_date


def generate_guid():
    """
    Generates a GUID for an anonymous user.
    :return: guid
    """
    guid = str(uuid.uuid4())
    return guid


def generate_request_metadata(request):
    """

    :return:
    """
