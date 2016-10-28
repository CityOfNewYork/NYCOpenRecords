#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    app.request.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for requests

"""
import uuid
from datetime import datetime

import os
from flask import render_template, current_app, url_for, request as flask_request
from flask_login import current_user
from tempfile import NamedTemporaryFile
from werkzeug.utils import secure_filename

from app import upload_redis
from app.constants import (
    event_type,
    role_name as role,
    ACKNOWLEDGEMENT_DAYS_DUE,
    user_type_request
)
from app.constants.user_type_auth import ANONYMOUS_USER
from app.constants.response_privacy import RELEASE_AND_PRIVATE
from app.constants.response_type import FILE
from app.constants.request_status import OPEN
from app.constants.submission_methods import DIRECT_INPUT
from app.lib.date_utils import get_following_date, get_due_date
from app.lib.db_utils import create_object, update_object
from app.lib.file_utils import get_mime_type
from app.lib.user_information import create_mailing_address
from app.models import (
    Requests,
    Agencies,
    Events,
    Users,
    UserRequests,
    Roles,
    Files,
    Responses
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
    date_created = datetime.now()
    date_submitted = (agency_date_submitted
                      if current_user.is_agency
                      else get_following_date(date_created))

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = get_due_date(date_submitted, ACKNOWLEDGEMENT_DAYS_DUE)

    # 5. Create Request
    request = Requests(
        id=request_id,
        title=title,
        agency_ein=agency,
        description=description,
        date_created=date_created,
        date_submitted=date_submitted,
        due_date=due_date,
        submission=submission,
        current_status=OPEN
    )
    create_object(request)

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
        metadata_id, metadata = _move_validated_upload(request_id, upload_path)

        # 8. Create response object
        response = Responses(request_id=request_id,
                             type=FILE,
                             date_modified=datetime.utcnow(),
                             metadata_id=metadata_id,
                             privacy=RELEASE_AND_PRIVATE)
        create_object(obj=response)

        # 8. Create upload Event
        upload_event = Events(user_id=user.guid,
                              auth_user_type=user.auth_user_type,
                              response_id=response.id,
                              request_id=request_id,
                              type=event_type.FILE_ADDED,
                              timestamp=datetime.utcnow(),
                              new_response_value=metadata.update(
                                  privacy=RELEASE_AND_PRIVATE))
        create_object(upload_event)

    role_to_user = {
        role.PUBLIC_REQUESTER: current_user.is_public,
        role.ANONYMOUS: current_user.is_anonymous,
        role.AGENCY_OFFICER: current_user.is_agency
    }
    role_name = [k for (k, v) in role_to_user.items() if v][0]
    # (key for "truthy" value)

    # 9. Create Event
    timestamp = datetime.utcnow()
    request_metadata = {
        'title': request.title,
        'description': request.description,
        'current_status': request.current_status,
        'due_date': request.due_date.isoformat()
    }
    event = Events(user_id=user.guid,
                   auth_user_type=user.auth_user_type,
                   request_id=request_id,
                   type=event_type.REQ_CREATED,
                   timestamp=timestamp,
                   new_response_value=request_metadata)
    create_object(event)
    if current_user.is_agency:
        agency_event = Events(user_id=current_user.guid,
                              auth_user_type=current_user.auth_user_type,
                              request_id=request.id,
                              type=event_type.REQ_CREATED,
                              timestamp=timestamp)
        create_object(agency_event)

    # 10. Create UserRequest
    user_request = UserRequests(user_guid=user.guid,
                                auth_user_type=user.auth_user_type,
                                request_user_type=user_type_request.REQUESTER,
                                request_id=request_id,
                                permissions=Roles.query.filter_by(
                                    name=role_name).first().permissions)
    create_object(user_request)

    # 11. Create the elasticsearch request doc
    # (Now that we can associate the request with its requester.)
    if current_app.config['ELASTICSEARCH_ENABLED']:
        request.es_create()

    # 12. Add all agency administrators to the request.

    # a. Get all agency administrators objects
    agency_administrators = Agencies.query.filter_by(ein=agency).first().administrators

    if agency_administrators:
        # Generate a list of tuples(guid, auth_user_type) identifying the agency administrators
        agency_administrators = [tuple(agency_user.split('::')) for agency_user in agency_administrators]

        # b. Store all agency users objects in the UserRequests table as Agency users with Agency Administrator
        # privileges
        for agency_administrator in agency_administrators:
            user_request = UserRequests(user_id=agency_administrator[0],
                                        auth_auth_user_type=agency_administrator[1],
                                        request_user_type=user_type_request.AGENCY,
                                        request_id=request_id,
                                        permissions=Roles.query.filter_by(name=role.AGENCY_ADMIN).first().permissions)
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
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    valid_name = os.path.basename(tmp_path).split('.', 1)[1]  # remove 'tmp' prefix
    valid_path = os.path.join(dst_dir, valid_name)
    os.rename(tmp_path, valid_path)
    upload_redis.set(
        get_upload_key(request_id, valid_name),
        upload_status.READY)

    # Store File Object
    size = os.path.getsize(valid_path)
    mime_type = get_mime_type(request_id, valid_name)
    file_obj = Files(name=valid_name, mime_type=mime_type, title='', size=size)
    create_object(obj=file_obj)

    file_metadata = {
        'name': valid_name,
        'mime_type': mime_type,
        'title': '',
        'size': size
    }
    return file_obj.id, file_metadata


def generate_request_id(agency_ein):
    """
    Generates an agency-specific FOIL request id.

    :param agency_ein: agency_ein ein used to generate the request_id
    :return: generated FOIL Request ID (FOIL - year - agency ein - 5 digits for request number)
    """
    if agency_ein:
        next_request_number = Agencies.query.filter_by(ein=agency_ein).first().next_request_number
        update_object({'next_request_number': next_request_number + 1},
                      Agencies,
                      agency_ein)
        request_id = "FOIL-{0:s}-{1:03d}-{2:05d}".format(
            datetime.now().strftime("%Y"), int(agency_ein), int(next_request_number))
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


def generate_request_metadata(request):
    """

    :return:
    """
    pass


def edit_requester_info(user_id, updated_info):
    """
    Update the requester's information for the specified request.

    :param user_id:
    :param updated_info: Dictionary of fields to values for the updated requester information.
    :return: If the operation was successful.
    """
    for key, value in updated_info.enumerate():
        # Loop through each value in the updated information and update the database
        if not update_object(attribute=key, value=value, obj_type=Users, obj_id=user_id):
            # TODO: Error message to Logfile
            # TODO: Raise exception with specific error message to alert the user
            return False

    return True


def send_confirmation_email(request, agency, user):
    """
    Sends out a confirmation email to requester and bcc the agency default email associated with the request.
    Also calls the add_email function to create a Emails object to be stored in the database.

    :param request: Requests object containing the new created request
    :param agency: Agencies object containing the agency of the new request
    :param user: Users object containing the user who created the request
    :return: sends an email to the requester and agency containing all information related to the request
    """
    subject = 'New Request Created ({})'.format(request.id)

    # get the agency's default email and adds it to the bcc list
    agency_default_email = agency.default_email
    agency_emails = []  # FIXME: Can this be empty?
    agency_emails.append(agency_default_email)
    bcc = agency_emails or ['agency@email.com']

    # gets the email and address information from the requester
    requester_email = user.email
    address = user.mailing_address

    # generates the view request page URL for this request
    page = flask_request.host_url.strip('/') + url_for('request.view', request_id=request.id)

    # grabs the html of the email message so we can store the content in the Emails object
    email_content = render_template("email_templates/email_confirmation.html", current_request=request,
                                    agency_name=agency.name, user=user, address=address)

    try:
        # if the requester supplied an email sent it to the request and bcc the agency
        if requester_email:
            safely_send_and_add_email(
                request.id,
                email_content,
                subject,
                "email_templates/email_confirmation",
                to=[requester_email],
                bcc=bcc,
                current_request=request,
                agency_name=agency,
                user=user,
                address=address,
                page=page
            )
        # otherwise send the email directly to the agency
        else:
            safely_send_and_add_email(
                request.id,
                email_content,
                subject,
                "email_templates/email_confirmation",
                to=[agency_default_email],
                current_request=request,
                agency_name=agency,
                user=user,
                address=address,
                page=page
            )
    except AssertionError:
        print('Must include: To, CC, or BCC')
    except Exception as e:
        print("Error:", e)
