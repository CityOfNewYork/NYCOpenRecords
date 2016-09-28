#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for requests

"""

import os
import random
import string
import uuid
from datetime import datetime

from business_calendar import FOLLOWING
from flask import render_template, current_app
from flask_login import current_user

from werkzeug.utils import secure_filename

from app import calendar
from app.constants import (
    ACKNOWLEDGEMENT_DAYS_DUE,
    EVENT_TYPE,
    ANONYMOUS_USER
)
from app.db_utils import create_object, update_object
from app.models import Requests, Agencies, Events, Users, UserRequests, Roles

DIRECT_INPUT = 'Direct Input'


def create_request(title,
                   description,
                   agency=None,
                   first_name=None,
                   last_name=None,
                   submission=DIRECT_INPUT,
                   agency_date_submitted=None,
                   email=None,
                   user_title=None,
                   organization=None,
                   phone=None,
                   fax=None,
                   address=None,
                   upload_file=None):
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
    request_id = generate_request_id(agency)

    # 2a. Generate Email Notification Text for Agency
    # agency_email = generate_email_template('agency_acknowledgment.html', request_id=request_id)
    # 2b. Generate Email Notification Text for Requester

    # 3a. Send Email Notification Text for Agency
    # 3b. Send Email Notification Text for Requester

    # 4a. Calculate Request Submitted Date (Round to next business day)
    date_created = datetime.now()
    date_submitted = (agency_date_submitted
                      if current_user.is_agency
                      else get_date_submitted(date_created))

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = get_due_date(date_submitted, ACKNOWLEDGEMENT_DAYS_DUE)

    # 5. Create Request
    request = Requests(
        id=request_id,
        title=title,
        agency=agency,
        description=description,
        date_created=date_created,
        date_submitted=date_submitted,
        due_date=due_date,
        submission=submission
    )
    create_object(request)

    # 6. Get or Create User
    if current_user.is_public:
        user = current_user
    else:
        user = Users(
            guid=generate_guid(),
            user_type=ANONYMOUS_USER,
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=user_title,
            organization=organization,
            email_validated=False,
            terms_of_use_accepted=False,
            phone_number=phone,
            fax_number=fax,
            mailing_address=address
        )
        create_object(user)

    if upload_file is not None:
        # 7. Store file in quarantine
        success = _save_request_upload(upload_file, request_id)

        # TODO: 6. Get file metadata (for Response record?)
        # TODO: update content.path once scanned & moved (celery task will take in request_id)
        # filesize = os.path.getsize(filepath)

        if success:
            # 8. Create upload Event
            upload_event = Events(user_id=user.guid,
                                  user_type=user.user_type,
                                  request_id=request_id,
                                  type=EVENT_TYPE['file_added'],
                                  timestamp=datetime.utcnow())
            create_object(upload_event)

    role_to_user = {
        'Public User - Requester': current_user.is_public,
        'Anonymous User': current_user.is_anonymous,
        'Agency FOIL Officer': current_user.is_agency
    }
    role_name = [k for (k, v) in role_to_user.items() if v][0]

    # 9. Create Event
    event = Events(user_id=user.guid,
                   user_type=user.user_type,
                   request_id=request_id,
                   type=EVENT_TYPE['request_created'],
                   timestamp=datetime.utcnow())
    create_object(event)

    # 10. Create UserRequest
    user_request = UserRequests(user_guid=user.guid,
                                user_type=user.user_type,
                                request_id=request_id,
                                permissions=Roles.query.filter_by(
                                    name=role_name).first().permissions)
    create_object(user_request)


def _save_request_upload(upload_file, request_id):
    success = True
    dir = os.path.join(
        current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
        request_id)
    if not os.path.exists(dir):
        os.mkdir(dir)
    filename = secure_filename(upload_file.filename)
    filepath = os.path.join(dir, filename)
    try:
        upload_file.save(filepath)
    except Exception as e:
        print("Error saving file {}: {}".format(filename, e))
        success = False
    return success


def generate_request_id(agency):
    """

    :param agency: agency ein used as a paramater to generate the request_id
    :return: generated FOIL Request ID (FOIL - year - agency ein - 5 digits for request number)
    """
    if agency:
        next_request_number = Agencies.query.filter_by(ein=agency).first().next_request_number
        update_object(attribute='next_request_number',
                      value=next_request_number + 1,
                      obj_type="Agencies",
                      obj_id=agency)
        request_id = "FOIL-{0:s}-{1:03d}-{2:05d}".format(
            datetime.now().strftime("%Y"), int(agency), int(next_request_number))
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
