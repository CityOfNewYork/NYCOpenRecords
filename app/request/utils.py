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
from urllib.parse import urljoin

from flask import render_template, current_app, url_for, request as flask_request
from flask_login import current_user
from werkzeug.utils import secure_filename

import app.lib.file_utils as fu
from app import upload_redis
from app.constants import (
    event_type,
    role_name as role,
    ACKNOWLEDGMENT_DAYS_DUE,
    user_type_request,
)
from app.constants.response_privacy import RELEASE_AND_PRIVATE
from app.constants.submission_methods import DIRECT_INPUT
from app.constants.user_type_auth import ANONYMOUS_USER
from app.lib.date_utils import get_following_date, get_due_date
from app.lib.db_utils import create_object, update_object
from app.lib.user_information import create_mailing_address
from app.lib.redis_utils import redis_set_file_metadata
from app.models import (
    Requests,
    Agencies,
    Events,
    Users,
    UserRequests,
    Roles,
    Files,
    ResponseTokens
)
from app.response.utils import safely_send_and_add_email
from app.upload.constants import upload_status
from app.upload.utils import (
    is_valid_file_type,
    scan_file,
    VirusDetectedException,
    get_upload_key
)


def create_request(title,
                   description,
                   category,
                   tz_name,
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
    :param tz_name: client's timezone name
    :param agency: agency_ein selected for the request
    :param first_name: first name of the requester
    :param last_name: last name of the requester
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
    date_created = datetime.utcnow()
    date_submitted = (agency_date_submitted
                      if current_user.is_agency
                      else get_following_date(date_created))

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = get_due_date(date_submitted, ACKNOWLEDGMENT_DAYS_DUE, tz_name)

    # 5. Create Request
    request = Requests(
        id=request_id,
        title=title,
        agency_ein=agency,
        category=category,
        description=description,
        date_created=date_created,
        date_submitted=date_submitted,
        due_date=due_date,
        submission=submission,
    )
    create_object(request)

    guid_for_event = current_user.guid if not current_user.is_anonymous else None
    auth_type_for_event = current_user.auth_user_type if not current_user.is_anonymous else None

    # 6. Get or Create User
    if current_user.is_public:
        user = current_user
    else:
        user = Users(
            guid=generate_guid(),
            auth_user_type=ANONYMOUS_USER,
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=user_title or None,
            organization=organization or None,
            email_validated=False,
            terms_of_use_accepted=False,
            phone_number=phone,
            fax_number=fax,
            mailing_address=address
        )
        create_object(user)
        # user created event
        create_object(Events(
            request_id,
            guid_for_event,
            auth_type_for_event,
            event_type.USER_CREATED,
            previous_value=None,
            new_value=user.val_for_events,
            response_id=None,
            timestamp=datetime.utcnow()
        ))

    if upload_path is not None:
        # 7. Move file to upload directory
        upload_path = _move_validated_upload(request_id, upload_path)
        # 8. Create response object
        filename = os.path.basename(upload_path)
        response = Files(request_id,
                         RELEASE_AND_PRIVATE,
                         filename,
                         filename,
                         fu.get_mime_type(upload_path),
                         fu.getsize(upload_path),
                         fu.get_hash(upload_path))
        create_object(obj=response)

        # 8. Create upload Event
        upload_event = Events(user_guid=user.guid,
                              auth_user_type=user.auth_user_type,
                              response_id=response.id,
                              request_id=request_id,
                              type_=event_type.FILE_ADDED,
                              timestamp=datetime.utcnow(),
                              new_value=response.val_for_events)
        create_object(upload_event)

        # Create response token if requester is anonymous
        if current_user.is_anonymous or current_user.is_agency:
            create_object(ResponseTokens(response.id))

    role_to_user = {
        role.PUBLIC_REQUESTER: user.is_public,
        role.ANONYMOUS: user.is_anonymous_requester,
    }
    role_name = [k for (k, v) in role_to_user.items() if v][0]
    # (key for "truthy" value)

    # 9. Create Event
    timestamp = datetime.utcnow()
    event = Events(user_guid=user.guid if current_user.is_anonymous else current_user.guid,
                   auth_user_type=user.auth_user_type if current_user.is_anonymous else current_user.auth_user_type,
                   request_id=request_id,
                   type_=event_type.REQ_CREATED,
                   timestamp=timestamp,
                   new_value=request.val_for_events)
    create_object(event)
    if current_user.is_agency:
        agency_event = Events(user_guid=current_user.guid,
                              auth_user_type=current_user.auth_user_type,
                              request_id=request.id,
                              type_=event_type.AGENCY_REQ_CREATED,
                              timestamp=timestamp)
        create_object(agency_event)

    # 10. Create UserRequest for requester
    user_request = UserRequests(user_guid=user.guid,
                                auth_user_type=user.auth_user_type,
                                request_user_type=user_type_request.REQUESTER,
                                request_id=request_id,
                                permissions=Roles.query.filter_by(
                                    name=role_name).first().permissions)
    create_object(user_request)
    create_object(Events(
        request_id,
        guid_for_event,
        auth_type_for_event,
        event_type.USER_ADDED,
        previous_value=None,
        new_value=user_request.val_for_events,
        response_id=None,
        timestamp=datetime.utcnow()
    ))

    # 11. Create the elasticsearch request doc only if agency has been onboarded
    agency = Agencies.query.filter_by(ein=agency).first()

    # (Now that we can associate the request with its requester.)
    if current_app.config['ELASTICSEARCH_ENABLED'] and agency.is_active:
        request.es_create()

    # 12. Add all agency administrators to the request.
    if agency.administrators:
        # b. Store all agency users objects in the UserRequests table as Agency users with Agency Administrator
        # privileges
        for admin in agency.administrators:
            user_request = UserRequests(user_guid=admin.guid,
                                        auth_user_type=admin.auth_user_type,
                                        request_user_type=user_type_request.AGENCY,
                                        request_id=request_id,
                                        permissions=Roles.query.filter_by(
                                            name=role.AGENCY_ADMIN).first().permissions)
            create_object(user_request)
            create_object(Events(
                request_id,
                guid_for_event,
                auth_type_for_event,
                event_type.USER_ADDED,
                previous_value=None,
                new_value=user_request.val_for_events,
                response_id=None,
                timestamp=datetime.utcnow()
            ))
    return request_id


def get_address(form):
    """
    Get mailing address from form data.

    :type form: app.request.forms.AgencyUserRequestForm
                app.request.forms.AnonymousRequestForm
    """
    return create_mailing_address(
        form.address.data or None,
        form.city.data or None,
        form.state.data or None,
        form.zipcode.data or None,
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
            print("Error saving file {} : {}".format(
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
    if not fu.exists(dst_dir):
        fu.mkdir(dst_dir)
    valid_name = os.path.basename(tmp_path).split('.', 1)[1]  # remove 'tmp' prefix
    valid_path = os.path.join(dst_dir, valid_name)
    # store file metadata in redis
    redis_set_file_metadata(request_id, tmp_path)
    fu.move(tmp_path, valid_path)
    upload_redis.set(
        get_upload_key(request_id, valid_name),
        upload_status.READY)
    return valid_path


def generate_request_id(agency_ein):
    """
    Generates an agency-specific FOIL request id.

    :param agency_ein: agency_ein ein used to generate the request_id
    :return: generated FOIL Request ID (FOIL - year - agency ein - 5 digits for request number)
    """
    if agency_ein:
        agency = Agencies.query.filter_by(ein=agency_ein).one()  # This is the actual agency (including sub-agencies)
        next_request_number = Agencies.query.filter_by(
            parent_ein=agency.parent_ein).one().next_request_number  # Parent agencies handle the request counting, not sub-agencies
        update_object({'next_request_number': next_request_number + 1},
                      Agencies,
                      agency_ein)
        agency_ein = agency.parent_ein
        request_id = "FOIL-{0:s}-{1!s}-{2:05d}".format(
            datetime.utcnow().strftime("%Y"), agency_ein, int(next_request_number))
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


def generate_guid():
    """
    Generates a GUID for an anonymous user.
    :return: the generated id
    """
    return str(uuid.uuid4())


def send_confirmation_email(request, agency, user):
    """
    Sends out a confirmation email to requester and bcc the agency default email associated with the request.
    Also calls the add_email function to create a Emails object to be stored in the database.

    :param request: Requests object containing the new created request
    :param agency: Agencies object containing the agency of the new request
    :param user: Users object containing the user who created the request
    """
    if agency.is_active:
        subject = 'New Request Created ({})'.format(request.id)
    else:
        subject = 'FOIL Request Submitted: {}'.format(request.title)

    # get the agency's default email and adds it to the bcc list
    bcc = [agency.default_email]

    # gets the email and address information from the requester
    requester_email = user.email
    address = user.mailing_address

    # generates the view request page URL for this request
    if agency.is_active:
        page = urljoin(flask_request.host_url, url_for('request.view', request_id=request.id))
    else:
        page = None

    # grabs the html of the email message so we can store the content in the Emails object
    email_content = render_template("email_templates/email_confirmation.html", current_request=request,
                                    agency_name=agency.name, user=user, address=address, page=page)

    try:
        # if the requester supplied an email sent it to the request and bcc the agency
        if requester_email:
            safely_send_and_add_email(
                request.id,
                email_content,
                subject,
                to=[requester_email],
                bcc=bcc,
            )
        # otherwise send the email directly to the agency
        else:
            safely_send_and_add_email(
                request.id,
                email_content,
                subject,
                to=[agency.default_email],
            )
    except AssertionError:
        print('Must include: To, CC, or BCC')
    except Exception as e:
        print("Error:", e)
