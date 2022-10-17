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
from app import upload_redis, sentry
from app.constants import (
    event_type,
    role_name as role,
    ACKNOWLEDGMENT_PERIOD_LENGTH,
    user_type_request,
    response_type
)
from app.constants.response_privacy import (
    RELEASE_AND_PRIVATE,
    PRIVATE
)
from app.constants.submission_methods import DIRECT_INPUT
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import (
    get_assigned_users_emails,
    send_contact_email
)
from app.lib.user_information import create_mailing_address
from app.lib.redis_utils import redis_set_file_metadata
from app.lib.date_utils import (
    get_following_date,
    get_due_date,
    local_to_utc,
    utc_to_local,
    is_business_day,
)
from app.models import (
    Requests,
    Agencies,
    Events,
    Emails,
    Users,
    UserRequests,
    Roles,
    Files,
    ResponseTokens,
    Responses,
)
from app.response.utils import (
    safely_send_and_add_email,
    get_file_links
)
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
                   agency_ein=None,
                   first_name=None,
                   last_name=None,
                   submission=DIRECT_INPUT,
                   agency_date_submitted_local=None,
                   email=None,
                   user_title=None,
                   organization=None,
                   phone=None,
                   fax=None,
                   address=None,
                   upload_path=None,
                   custom_metadata=None):
    """
    Creates a new FOIL Request and associated Users, UserRequests, and Events.

    :param title: request title
    :param description: detailed description of the request
    :param tz_name: client's timezone name
    :param agency_ein: agency_ein selected for the request
    :param first_name: first name of the requester
    :param last_name: last name of the requester
    :param submission: request submission method
    :param agency_date_submitted_local: submission date chosen by agency
    :param email: requester's email address
    :param user_title: requester's organizational title
    :param organization: requester's organization
    :param phone: requester's phone number
    :param fax: requester's fax number
    :param address: requester's mailing address
    :param upload_path: file path of the validated upload
    :param custom_metadata: JSON containing all data from custom request forms
    """
    # 1. Generate the request id
    request_id = generate_request_id(agency_ein)

    # 2a. Generate Email Notification Text for Agency
    # agency_email = generate_email_template('agency_acknowledgment.html', request_id=request_id)
    # 2b. Generate Email Notification Text for Requester

    # 3a. Send Email Notification Text for Agency
    # 3b. Send Email Notification Text for Requester

    # 4a. Calculate Request Submitted Date (Round to next business day)
    date_created_local = utc_to_local(datetime.utcnow(), tz_name)
    if current_user.is_agency:
        date_submitted_local = agency_date_submitted_local
    else:
        date_submitted_local = date_created_local

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = get_due_date(
        date_submitted_local,
        ACKNOWLEDGMENT_PERIOD_LENGTH,
        tz_name)

    date_created = local_to_utc(date_created_local, tz_name)
    date_submitted = local_to_utc(date_submitted_local, tz_name)

    # 5. Create Request
    request = Requests(
        id=request_id,
        title=title,
        agency_ein=agency_ein,
        category=category,
        description=description,
        date_created=date_created,
        date_submitted=date_submitted,
        due_date=due_date,
        submission=submission,
        custom_metadata=custom_metadata
    )
    create_object(request)

    guid_for_event = current_user.guid if not current_user.is_anonymous else None

    # 6. Get or Create User
    if current_user.is_public:
        user = current_user
    else:
        user = Users(
            guid=generate_guid(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            title=user_title or None,
            organization=organization or None,
            email_validated=False,
            terms_of_use_accepted=False,
            phone_number=phone,
            fax_number=fax,
            mailing_address=address,
            is_anonymous_requester=True
        )
        create_object(user)
        # user created event
        create_object(Events(
            request_id,
            guid_for_event,
            event_type.USER_CREATED,
            previous_value=None,
            new_value=user.val_for_events,
            response_id=None,
            timestamp=datetime.utcnow()
        ))

    if upload_path is not None:
        # Store file metadata
        file_mimetype = fu.get_mime_type(upload_path)
        file_size = fu.getsize(upload_path)
        file_hash = fu.get_hash(upload_path)

        # 7. Move file to upload directory
        upload_path = _move_validated_upload(request_id, upload_path)
        # 8. Create response object
        filename = os.path.basename(upload_path)
        response = Files(request_id,
                         RELEASE_AND_PRIVATE,
                         filename,
                         filename,
                         file_mimetype,
                         file_size,
                         file_hash,
                         is_editable=False)
        create_object(obj=response)

        # 8. Create upload Event
        upload_event = Events(user_guid=user.guid,
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
                   request_id=request_id,
                   type_=event_type.REQ_CREATED,
                   timestamp=timestamp,
                   new_value=request.val_for_events)
    create_object(event)
    if current_user.is_agency:
        agency_event = Events(user_guid=current_user.guid,
                              request_id=request.id,
                              type_=event_type.AGENCY_REQ_CREATED,
                              timestamp=timestamp)
        create_object(agency_event)

    # 10. Create UserRequest for requester
    user_request = UserRequests(user_guid=user.guid,
                                request_user_type=user_type_request.REQUESTER,
                                request_id=request_id,
                                permissions=Roles.query.filter_by(
                                    name=role_name).first().permissions)
    create_object(user_request)
    create_object(Events(
        request_id,
        guid_for_event,
        event_type.USER_ADDED,
        previous_value=None,
        new_value=user_request.val_for_events,
        response_id=None,
        timestamp=datetime.utcnow()
    ))

    # 11. Create the elasticsearch request doc only if agency has been onboarded
    agency = Agencies.query.filter_by(ein=agency_ein).one()

    # 12. Add all agency administrators to the request.
    if agency.administrators:
        # b. Store all agency users objects in the UserRequests table as Agency users with Agency Administrator
        # privileges
        _create_agency_user_requests(request_id=request_id,
                                     agency_admins=agency.administrators,
                                     guid_for_event=guid_for_event)

    # 13. Add all parent agency administrators to the request.
    if agency != agency.parent:
        if (
                agency.parent.agency_features is not None and
                agency_ein in agency.parent.agency_features.get('monitor_agency_requests', []) and
                agency.parent.is_active and
                agency.parent.administrators
        ):
            _create_agency_user_requests(request_id=request_id,
                                         agency_admins=agency.parent.administrators,
                                         guid_for_event=guid_for_event)

    # (Now that we can associate the request with its requester AND agency users.)
    if current_app.config['ELASTICSEARCH_ENABLED'] and agency.is_active:
        request.es_create()

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
            sentry.captureException()
            print("Error saving file {} : {}".format(
                file_field.data.filename, e))
            file_field.errors.append('Error saving file.')
        else:
            try:
                scan_file(path)
            except VirusDetectedException:
                sentry.captureException()
                file_field.errors.append('File is infected.')
            except Exception:
                sentry.captureException()
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

    # Move file to data directory if volume storage is enabled
    if current_app.config['USE_VOLUME_STORAGE']:
        fu.move(tmp_path, valid_path)
    # Upload file to Azure if Azure storage is enabled
    elif current_app.config['USE_AZURE_STORAGE']:
        fu.azure_upload(tmp_path, valid_path)

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
        agency = Agencies.query.filter_by(
            ein=agency_ein).one()  # This is the actual agency (including sub-agencies)
        next_request_number = Agencies.query.filter_by(
            ein=agency.formatted_parent_ein).one().next_request_number  # Parent agencies handle the request counting, not sub-agencies
        agency_ein = agency.parent_ein
        request_id = "FOIL-{0:s}-{1!s}-{2:05d}".format(
            datetime.utcnow().strftime("%Y"), agency_ein, int(next_request_number))
        if Requests.query.filter_by(id=request_id).one_or_none():
            update_object(
                {'next_request_number': next_request_number + 1},
                Agencies,
                agency.ein
            )
            request_id = generate_request_id(agency.ein)
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
        subject = 'Request {} Submitted to {}'.format(request.id, agency.name)
    else:
        subject = 'FOIL Request Submitted to {}'.format(agency.name)

    # get the agency's default email and adds it to the bcc list
    bcc = [agency.default_email]

    # gets the email and address information from the requester
    requester_email = user.email
    address = user.mailing_address

    # gets the file link, if a file was provided.
    file_response = request.responses.filter(Responses.type == response_type.FILE).one_or_none()
    release_public, release_private, private = ([] for i in range(3))

    if file_response is not None:
        get_file_links(file_response, release_public, release_private, private)
    file_link = release_private[0] if len(release_private) > 0 else None

    # generates the view request page URL for this request
    if agency.is_active:
        page = urljoin(flask_request.host_url, url_for('request.view', request_id=request.id))
        email_template = "email_templates/email_confirmation.html"
        agency_default_email = None
    else:
        page = None
        email_template = "email_templates/email_not_onboarded.html"
        agency_default_email = agency.default_email

    # Determine if custom request forms are enabled
    if 'enabled' in request.agency.agency_features['custom_request_forms']:
        custom_request_forms_enabled = request.agency.agency_features['custom_request_forms']['enabled']
    else:
        custom_request_forms_enabled = False

    # Determine if request description should be hidden when custom forms are enabled
    if 'description_hidden_by_default' in request.agency.agency_features['custom_request_forms']:
        description_hidden_by_default = request.agency.agency_features['custom_request_forms'][
            'description_hidden_by_default']
    else:
        description_hidden_by_default = False

    # grabs the html of the email message so we can store the content in the Emails object
    email_content = render_template(email_template,
                                    current_request=request,
                                    agency_name=agency.name,
                                    agency_default_email=agency_default_email,
                                    user=user,
                                    address=address,
                                    file_link=file_link,
                                    page=page,
                                    custom_request_forms_enabled=custom_request_forms_enabled,
                                    description_hidden_by_default=description_hidden_by_default)

    try:
        # if the requester supplied an email, send it to the request and bcc the agency
        if requester_email:
            safely_send_and_add_email(
                request.id,
                email_content,
                subject,
                to=[requester_email],
                bcc=bcc,
                reply_to=agency.default_email,
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
        sentry.captureException()
        print('Must include: To, CC, or BCC')
    except Exception as e:
        sentry.captureException()
        print("Error:", e)


def _create_agency_user_requests(request_id, agency_admins, guid_for_event):
    """
    Creates user_requests entries for agency administrators.
    :param request_id: Request being created
    :param agency_users: List of Users
    :param guid_for_event: guid used to create request events
    :return:
    """

    for admin in agency_admins:
        user_request = UserRequests(user_guid=admin.guid,
                                    request_user_type=user_type_request.AGENCY,
                                    request_id=request_id,
                                    permissions=Roles.query.filter_by(
                                        name=role.AGENCY_ADMIN).first().permissions)
        create_object(user_request)
        create_object(Events(
            request_id,
            guid_for_event,
            event_type.USER_ADDED,
            previous_value=None,
            new_value=user_request.val_for_events,
            response_id=None,
            timestamp=datetime.utcnow()
        ))


def create_contact_record(request, first_name, last_name, email, subject, message):
    """
    Creates Users, Emails, and Events entries for a contact submission for a request.
    Sends email with message to all agency users associated with the request.

    :param request: request object
    :param first_name: sender's first name
    :param last_name: sender's last name
    :param email: sender's email
    :param subject: subject of email
    :param message: email body
    """
    if current_user == request.requester:
        user = current_user
    else:
        user = Users(
            guid=generate_guid(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            email_validated=False,
            terms_of_use_accepted=False,
            is_anonymous_requester=True
        )
        create_object(user)

        create_object(Events(
            request_id=request.id,
            user_guid=None,
            type_=event_type.USER_CREATED,
            new_value=user.val_for_events
        ))

    body = "Name: {} {}\n\nEmail: {}\n\nSubject: {}\n\nMessage:\n{}".format(
        first_name, last_name, email, subject, message)

    agency_emails = get_assigned_users_emails(request.id)

    email_obj = Emails(
        request.id,
        PRIVATE,
        to=','.join([email.replace('{', '').replace('}', '') for email in agency_emails]),
        cc=None,
        bcc=None,
        subject=subject,
        body=body
    )

    create_object(email_obj)

    create_object(Events(
        request_id=request.id,
        user_guid=user.guid,
        type_=event_type.CONTACT_EMAIL_SENT,
        response_id=email_obj.id,
        new_value=email_obj.val_for_events
    ))

    send_contact_email(
        subject,
        agency_emails,
        message,
        email
    )
