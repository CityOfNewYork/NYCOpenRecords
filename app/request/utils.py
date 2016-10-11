#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for requests

"""

import os
import uuid
from datetime import datetime
from tempfile import NamedTemporaryFile

from business_calendar import FOLLOWING
from flask import render_template, current_app
from flask_login import current_user

from werkzeug.utils import secure_filename

from app import calendar, upload_redis
from app.constants import (
    ACKNOWLEDGEMENT_DAYS_DUE,
    EVENT_TYPE,
    ANONYMOUS_USER,
    ROLE_NAME
)
from app.lib.db_utils import create_object, update_object
from app.lib.user_information import create_mailing_address
from app.models import Requests, Agencies, Events, Users, UserRequests, Roles
from app.upload.constants import UPLOAD_STATUS
from app.upload.utils import (
    is_valid_file_type,
    scan_file,
    VirusDetectedException,
    get_upload_key
)

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
                   upload_path=None):
    """
    Creates a new FOIL Request and associated Users, UserRequests, and Events.

    :param title: request title
    :param description: detailed description of the request
    :param agency: agency selected for the request
    :param date_created: date the request was made
    :param submission: request submission method
    :param agency_date_submitted: submission date chosen by agency
    :param email: requester's email address
    :param user_title: requester's organizational title
    :param organization: requester's organization
    :param phone: requester's phone number
    :param fax: requester's fax number
    :param address: requester's mailing address
    :param upload_path: file path of the validated upload
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

    if upload_path is not None:
        # 7. Move file to upload directory
        _move_validated_upload(request_id, upload_path)
        # 8. Create upload Event
        upload_event = Events(user_id=user.guid,
                              user_type=user.user_type,
                              request_id=request_id,
                              type=EVENT_TYPE['file_added'],
                              timestamp=datetime.utcnow())
        create_object(upload_event)

    role_to_user = {
        ROLE_NAME.PUBLIC_REQUESTER : current_user.is_public,
        ROLE_NAME.ANONYMOUS: current_user.is_anonymous,
        ROLE_NAME.AGENCY_OFFICER: current_user.is_agency
    }
    role_name = [k for (k, v) in role_to_user.items() if v][0]
    # (key for "truthy" value)

    # 9. Create Event
    timestamp = datetime.utcnow()
    event = Events(user_id=user.guid,
                   user_type=user.user_type,
                   request_id=request_id,
                   type=EVENT_TYPE['request_created'],
                   timestamp=timestamp)
    create_object(event)
    if current_user.is_agency:
        agency_event = Events(user_id=current_user.guid,
                              user_type=current_user.user_type,
                              request_id=request.id,
                              type=EVENT_TYPE['request_created'],
                              timestamp=timestamp)
        create_object(agency_event)

    # 10. Create UserRequest
    user_request = UserRequests(user_guid=user.guid,
                                user_type=user.user_type,
                                request_id=request_id,
                                permissions=Roles.query.filter_by(
                                    name=role_name).first().permissions)
    create_object(user_request)
    return request_id


def get_address(form):
    """
    Get mailing address from form data.

    :type form: app.request.forms.AgencyUserRequestForm
                app.request.forms.AnonymousRequestForm
    """
    return create_mailing_address(
        form.address.data,
        form.city.data,
        form.state.data,
        form.zipcode.data,
        form.address_two.data or None
    )


def handle_upload_no_id(file_field):
    """
    Try to store and scan an uploaded file when no request id
    has been generated. Return the stored upload file path
    on success, otherwise add errors to the file field.

    :param file_field: form file field

    :return: the file path to the stored upload
    """
    path = None
    valid_file_type, file_type = is_valid_file_type(file_field.data)
    if not valid_file_type:
        file_field.errors.append(
            "File type '{}' is not allowed.".format(file_type))
    else:
        try:
            path = _quarantine_upload_no_id(file_field.data)
        except Exception as e:
            print("Error saving file {} : {}". format(
                file_field.data.filename, e))
            file_field.errors.append('Error saving file.')
        else:
            try:
                scan_file(path)
            except VirusDetectedException:
                file_field.errors.append('File is infected.')
            except Exception:
                file_field.errors.append('Error scanning file.')
    return path


def _quarantine_upload_no_id(upload_file):
    """
    Save an upload file to the quarantine directory, with
    this directory being the file's immediate parent.

    This file should not exist after the completion of the
    create-request pipeline and is therefore treated explicitly
    as temporary (its name is prefixed with an indicator).

    :type upload_file: werkzeug.datastructures.FileStorage
    :return: the file path to the quarantined upload
    """
    with NamedTemporaryFile(
        dir=current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
        suffix='.{}'.format(secure_filename(upload_file.filename)),
        delete=False
    ) as fp:
        upload_file.save(fp)
        return fp.name


def _move_validated_upload(request_id, tmp_path):
    """
    Move an approved upload to the upload directory.

    :param request_id: the id of the request associated with the upload
    :param tmp_path: the temporary file path to the upload
        generated by app.request.utils._quarantine_upload_no_id()
    """
    dst_dir = os.path.join(
        current_app.config['UPLOAD_DIRECTORY'],
        request_id)
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    valid_name = os.path.basename(tmp_path).split('.', 1)[1]  # remove 'tmp' prefix
    valid_path = os.path.join(dst_dir, valid_name)
    os.rename(tmp_path, valid_path)
    upload_redis.set(
        get_upload_key(request_id, valid_name),
        UPLOAD_STATUS.READY)


def generate_request_id(agency):
    """
    Generates an agency-specific FOIL request id.

    :param agency: agency ein used to generate the request_id
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
    Generate HTML for rich-text emails.

    :param template_name: specific email template
    :param kwargs:
    :return: email template
    """
    return render_template(template_name, **kwargs)


def get_date_submitted(date_created):
    """
    Generates the date submitted for a request.

    :param date_created: date the request was made
    :return: date submitted which is the date_created rounded off to the next business day
    """
    return calendar.addbusdays(date_created, FOLLOWING)


def get_due_date(date_submitted, days_until_due, hour_due=17, minute_due=00, second_due=00):
    """
    Generates the due date for a request.

    :param date_submitted: date submitted which is the date_created rounded off to the next business day
    :param days_until_due: number of business days until a request is due
    :param hour_due: Hour when the request will be marked as overdue, defaults to 1700 (5 P.M.)
    :param minute_due: Minute when the request will be marked as overdue, defaults to 00 (On the hour)
    :param second_due: Second when the request will be marked as overdue, defaults to 00

    :return: due date which is 5 business days after the date_submitted and time is always 5:00 PM
    """
    calc_due_date = calendar.addbusdays(date_submitted, days_until_due)  # calculates due date
    return calc_due_date.replace(hour=hour_due, minute=minute_due, second=second_due)  # sets time to 5:00 PM


def generate_guid():
    """
    Generates a GUID for an anonymous user.
    :return: the generated id
    """
    return str(uuid.uuid4())


def generate_request_metadata(request):
    """

    :return:
    """
    pass
