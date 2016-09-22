#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for requests

"""

from app import calendar
from app.models import Request, Agency, Event, User
from app.db_utils import create_object, update_object
from app.constants import ACKNOWLEDGEMENT_DAYS_DUE, event_type, user_type
from datetime import datetime
from business_calendar import FOLLOWING
from flask import render_template
# FOR TESTING
import random
import string


def process_request(title=None, description=None, agency=None, submission='Direct Input'):
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
    request_id = generate_request_id()

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

    # 7. Create Request object
    req = Request(id=request_id, title=title, description=description, date_created=date_created,
                  date_submitted=date_submitted, due_date=due_date, submission=submission)
    # 8. Store Request object
    create_object(obj=req)

    # 9. Create Event object
    event = Event(request_id=request_id, type=event_type['request_created'], timestamp=datetime.utcnow())

    # 10. Store Event object
    create_object(obj=event)


def process_anon_request(agency, title, description, email, first_name, last_name, user_title, organization, phone, fax,
                         address):
    """
    Function for creating and storing a new request from an anonymous user on the backend.

    :param agency: agency ein used as a parameter to create user in database
    :param title: request title
    :param description: detailed description of the request
    :param email: requester's email
    :param first_name: requester's first name
    :param last_name: requester's last name
    :param user_title: requester's title
    :param company: requester's organization
    :param phone: requester's phone number
    :param fax: requester's fax number
    :param address: requester's address
    :return: creates and stores the new FOIL request from an anonymous user
             Request, Event, and User table are updated in the database
    """
    # Creates and stores Request and Event object
    process_request(agency=agency, title=title, description=description)
    guid = generate_guid()

    # Creates User object
    user = User(guid=guid, user_type=user_type['anonymous_user'], email=email, first_name=first_name,
                last_name=last_name, title=user_title, organization=organization, email_validated=False,
                terms_of_use_accepted=False, phone_number=phone, fax_number=fax, mailing_address=address)

    # Store User object
    create_object(obj=user)


def process_agency_request(agency, title, description, submission, email, first_name, last_name, user_title,
                           organization, phone, fax, address):
    """
    Function for creating an storing a new request from an agency user on the backend.

    :param agency: agency ein used as a parameter to create user in database
    :param title: request title
    :param description: detailed description of the request
    :param submission: format the request was received
    :param email: requester's email
    :param first_name: requester's first name
    :param last_name: requester's last name
    :param user_title: requester's title
    :param company: requester's organization
    :param phone: requester's phone number
    :param fax: requester's fax number
    :param address: requester's address
    :return: creates and stores the new FOIL request from an agency user
             Request, Event, and User table are updated in the database

    """
    # Creates and stores Request and Event object
    process_request(agency=agency, title=title, description=description, submission=submission)
    guid = generate_guid()

    # Creates User object
    user = User(guid=guid, user_type=user_type['agency_user'], email=email, first_name=first_name,
                last_name=last_name, title=user_title, organization=organization, email_validated=False,
                terms_of_use_accepted=False, phone_number=phone, fax_number=fax, mailing_address=address)

    # Store User object
    create_object(obj=user)


def generate_request_id():
    """

    :param agency: agency ein used as a paramater to generate the request_id
    :return: generated FOIL Request ID (FOIL - year - agency ein - 5 digits for request number)
    """
    # next_request_number = Agency.query.filter_by(ein=agency).first().next_request_number
    # update_object(type="agency", field="next_request_number", value=next_request_number + 1)
    # request_id = 'FOIL-{}-{}-{}'.format(datetime.now().strftime("%Y"), agency, next_request_number)
    # FOR TESTING: remove agency in function argument and comment out above, uncomment below
    request_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return request_id


def generate_guid():
    """
    FOR TESTING: function that generates a guid
    :return: guid
    """
    guid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))
    return guid


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
