"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
import os
import re
import json

import app.lib.file_utils as fu

from datetime import datetime
from abc import ABCMeta, abstractmethod
from urllib.parse import urljoin, urlencode

from cached_property import cached_property
from werkzeug.utils import secure_filename
from flask_login import current_user
from flask import (
    current_app,
    request as flask_request,
    render_template,
    url_for,
    jsonify
)
from app import email_redis, calendar
from app.constants import (
    event_type,
    response_type,
    response_privacy,
    request_status,
    determination_type,
    UPDATED_FILE_DIRNAME,
    DELETED_FILE_DIRNAME,
    DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS,
    EMAIL_TEMPLATE_FOR_TYPE
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PUBLIC, RELEASE_AND_PRIVATE
from app.constants import permission
from app.lib.date_utils import (
    get_due_date,
    process_due_date,
    get_release_date,
    get_timezone_offset
)
from app.lib.db_utils import create_object, update_object, delete_object
from app.lib.email_utils import send_email, get_agency_emails
from app.lib.redis_utils import redis_get_file_metadata, redis_delete_file_metadata
from app.lib.utils import eval_request_bool, UserRequestException
from app.models import (
    Events,
    Notes,
    Files,
    Links,
    Instructions,
    Requests,
    Responses,
    Reasons,
    Determinations,
    Emails,
    ResponseTokens,
    Users,
)


# TODO: class ResponseProducer()

def add_file(request_id, filename, title, privacy, is_editable):
    """
    Create and store the file response object for the specified request.
    Gets the file mimetype and magic file check from a helper function in lib.file_utils
    File privacy options can be either Release and Public, Release and Private, or Private.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: Request ID that the file is being added to
    :param filename: The secured_filename of the file.
    :param title: The title of the file which is entered by the uploader.
    :param privacy: The privacy option of the file.

    """
    path = os.path.join(current_app.config['UPLOAD_DIRECTORY'], request_id, filename)
    try:
        size, mime_type, hash_ = redis_get_file_metadata(request_id, path)
        redis_delete_file_metadata(request_id, path)
    except AttributeError:
        size = fu.getsize(path)
        mime_type = fu.get_mime_type(path)
        hash_ = fu.get_hash(path)

    response = Files(
        request_id,
        privacy,
        title,
        filename,
        mime_type,
        size,
        hash_,
        is_editable=is_editable
    )
    create_object(response)

    create_response_event(event_type.FILE_ADDED, response)

    return response


def add_note(request_id, note_content, email_content, privacy, is_editable):
    """
    Create and store the note object for the specified request.
    Store the note content into the Notes table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the note
    :param note_content: string content of the note to be created and stored as a note object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the note

    """
    response = Notes(request_id, privacy, note_content, is_editable=is_editable)
    create_object(response)
    create_response_event(event_type.NOTE_ADDED, response)
    if privacy != PRIVATE:
        subject = 'Response Added to {} - Note'.format(request_id)
    else:
        subject = 'Note Added to {}'.format(request_id)
    _send_response_email(request_id,
                         privacy,
                         email_content,
                         subject)


def add_acknowledgment(request_id, info, days, date, tz_name, email_content):
    """
    Create and store an acknowledgement-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param info: additional information pertaining to the acknowledgment
    :param days: days until request completion
    :param date: date of request completion
    :param tz_name: client's timezone name
    :param email_content: email body associated with the acknowledgment

    """
    if not Requests.query.filter_by(id=request_id).one().was_acknowledged:
        new_due_date = _get_new_due_date(request_id, days, date, tz_name)
        update_object(
            {'due_date': new_due_date,
             'status': request_status.IN_PROGRESS},
            Requests,
            request_id
        )
        privacy = RELEASE_AND_PUBLIC
        response = Determinations(
            request_id,
            privacy,
            determination_type.ACKNOWLEDGMENT,
            info,
            new_due_date,
        )
        create_object(response)
        create_response_event(event_type.REQ_ACKNOWLEDGED, response)
        _send_response_email(request_id,
                             privacy,
                             email_content,
                             'Request {} Acknowledged'.format(request_id))


def add_denial(request_id, reason_ids, email_content):
    """
    Create and store a denial-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param reason_ids: reason for denial
    :param email_content: email body associated with the denial

    """
    if Requests.query.filter_by(id=request_id).one().status != request_status.CLOSED:
        update_object(
            {'status': request_status.CLOSED},
            Requests,
            request_id
        )
        privacy = RELEASE_AND_PUBLIC
        response = Determinations(
            request_id,
            privacy,
            determination_type.DENIAL,
            "|".join(Reasons.query.filter_by(id=reason_id).one().content
                     for reason_id in reason_ids)
        )
        create_object(response)
        create_response_event(event_type.REQ_CLOSED, response)
        update_object(
            {'agency_description_release_date': calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)},
            Requests,
            request_id
        )
        _send_response_email(request_id,
                             privacy,
                             email_content,
                             'Request {} Closed'.format(request_id))


def add_closing(request_id, reason_ids, email_content):
    """
    Create and store a closing-determination response for the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param reason_ids: reason(s) for closing
    :param email_content: email body associated with the closing

    """
    current_request = Requests.query.filter_by(id=request_id).one()
    if current_request.status != request_status.CLOSED:
        if current_request.privacy['agency_description'] or not current_request.agency_description:
            for privacy in current_request.responses.with_entities(Responses.privacy, Responses.type).filter(
                            Responses.type != response_type.NOTE, Responses.type != response_type.EMAIL).all():
                if privacy[0] != RELEASE_AND_PUBLIC:
                    raise UserRequestException(action="close",
                                               request_id=current_request.id,
                                               reason="Agency Description is private and responses are not public"
                                               )
            if current_request.privacy['title']:
                raise UserRequestException(action="close",
                                           request_id=current_request.id,
                                           reason="Agency Description is private and title is private"
                                           )
        update_object(
            {'status': request_status.CLOSED},
            Requests,
            request_id
        )
        privacy = RELEASE_AND_PUBLIC
        response = Determinations(
            request_id,
            privacy,
            determination_type.CLOSING,
            "|".join(Reasons.query.filter_by(id=reason_id).one().content
                     for reason_id in reason_ids)
        )
        create_object(response)
        create_response_event(event_type.REQ_CLOSED, response)
        update_object(
            {'agency_description_release_date': calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)},
            Requests,
            request_id
        )
        _send_response_email(request_id,
                             privacy,
                             email_content,
                             'Request {} Closed'.format(request_id))


def add_reopening(request_id, date, tz_name, email_content):
    """
    Create and store a re-opened-determination for the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param date: string of new date of request completion
    :param tz_name: client's timezone name
    :param email_content: email body associated with the reopened request

    """
    if Requests.query.filter_by(id=request_id).one().status == request_status.CLOSED:
        new_due_date = process_due_date(datetime.strptime(date, '%Y-%m-%d'), tz_name)
        privacy = RELEASE_AND_PUBLIC
        response = Determinations(
            request_id,
            privacy,
            determination_type.REOPENING,
            None,
            new_due_date
        )
        create_object(response)
        create_response_event(event_type.REQ_REOPENED, response)
        update_object(
            {'status': request_status.IN_PROGRESS,
             'due_date': new_due_date,
             'agency_description_release_date': None},
            Requests,
            request_id
        )
        _send_response_email(request_id,
                             privacy,
                             email_content,
                             'Request {} Re-Opened'.format(request_id))


def add_extension(request_id, length, reason, custom_due_date, tz_name, email_content):
    """
    Create and store the extension object for the specified request.
    Extension's privacy is always Release and Public.
    Provides parameters for the process_response function to create and store responses and events object.
    Calls email notification function to email both requester and agency users detailing the extension.

    :param request_id: FOIL request ID for the extension
    :param length: length in business days that the request is being extended by
    :param reason: reason for the extension of the request
    :param custom_due_date: if custom_due_date is inputted from the frontend, the new extended date of the request
    :param tz_name: client's timezone name
    :param email_content: email body content of the email to be created and stored as a email object

    """
    new_due_date = _get_new_due_date(request_id, length, custom_due_date, tz_name)
    update_object(
        {'due_date': new_due_date},
        Requests,
        request_id)
    privacy = RELEASE_AND_PUBLIC
    response = Determinations(
        request_id,
        privacy,
        determination_type.EXTENSION,
        reason,
        new_due_date
    )
    create_object(response)
    create_response_event(event_type.REQ_EXTENDED, response)
    _send_response_email(request_id,
                         privacy,
                         email_content,
                         'Request {} Extended'.format(request_id))


def add_link(request_id, title, url_link, email_content, privacy, is_editable=True):
    """
    Create and store the link object for the specified request.
    Store the link content into the Links table.
    Provides parameters for the process_response function to create and store responses and events object
    Calls email notification function to email both requester and agency users detailing the link.

    :param request_id: FOIL request ID for the link
    :param title: title of the link to be stored in the Links table and as a response value
    :param url_link: link url to be stored in the Links table and as a response value
    :param email_content: string of HTML email content to be created and stored as a email object
    :param privacy: The privacy option of the link

    """
    response = Links(request_id, privacy, title, url_link, is_editable=is_editable)
    create_object(response)
    create_response_event(event_type.LINK_ADDED, response)
    if privacy != PRIVATE:
        subject = 'Response Added to {} - Link'.format(request_id)
    else:
        subject = 'Link Added to {}'.format(request_id)
    _send_response_email(request_id,
                         privacy,
                         email_content,
                         subject)


def add_instruction(request_id, instruction_content, email_content, privacy, is_editable=True):
    """
    Creates and stores the instruction object for the specified request.
    Stores the instruction content into the Instructions table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the instruction
    :param instruction_content: string content of the instruction to be created and stored as a instruction object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the instruction

    """
    response = Instructions(request_id, privacy, instruction_content, is_editable=is_editable)
    create_object(response)
    create_response_event(event_type.INSTRUCTIONS_ADDED, response)
    if privacy != PRIVATE:
        subject = 'Response Added to {} - Offline Access Instructions'.format(request_id)
    else:
        subject = 'Offline Instructions Added to {}'.format(request_id)
    _send_response_email(request_id,
                         privacy,
                         email_content,
                         subject)


def _add_email(request_id, subject, email_content, to=None, cc=None, bcc=None):
    """
    Create and store the email object for the specified request.
    Store the email metadata into the Emails table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: takes in FOIL request ID as an argument for the process_response function
    :param subject: subject of the email to be created and stored as a email object
    :param email_content: string of HTML email content to be created and stored as a email object
    :param to: list of person(s) email is being sent to
    :param cc: list of person(s) email is being cc'ed to
    :param bcc: list of person(s) email is being bcc'ed

    """
    to = ','.join([email.replace('{', '').replace('}', '') for email in to]) if to else None
    cc = ','.join([email.replace('{', '').replace('}', '') for email in cc]) if cc else None
    bcc = ','.join([email.replace('{', '').replace('}', '') for email in bcc]) if bcc else None

    response = Emails(
        request_id,
        PRIVATE,
        to,
        cc,
        bcc,
        subject,
        body=email_content
    )
    create_object(response)
    create_response_event(event_type.EMAIL_NOTIFICATION_SENT, response)


def add_sms():
    """
    Will add an SMS to the database for the specified request.
    :return:
    """
    # TODO: Implement adding an SMS
    pass


def add_push():
    """
    Will add a push to the database for the specified request.
    :return:
    """
    # TODO: Implement adding a push
    pass


def _get_new_due_date(request_id, extension_length, custom_due_date, tz_name):
    """
    Gets the new due date from either generating with extension length, or setting from an inputted custom due date.
    If the extension length is -1, then we use the custom_due_date to determine the new_due_date.
    Or else, extension length has an length (20, 30, 60, 90, or 120) and new_due_date will be determined by
    generate_due_date.

    :param request_id: FOIL request ID that is being passed in to generate_new_due_date
    :param extension_length: number of days the due date is being extended by
    :param custom_due_date: custom due date of the request (string in format '%Y-%m-%d')
    :param tz_name: client's timezone name

    :return: new_due_date of the request
    """
    if extension_length == '-1':
        new_due_date = process_due_date(datetime.strptime(custom_due_date, '%Y-%m-%d'),
                                        tz_name)
    else:
        new_due_date = get_due_date(
            Requests.query.filter_by(id=request_id).one().due_date,
            int(extension_length),
            tz_name
        )
    return new_due_date


def process_upload_data(form):
    """
    Helper function that processes the uploaded file form data.
    A files dictionary is first created and then populated with keys and their respective values of the form data.

    :param form: form object to be processed and separated into appropriate keys and values

    :return: A dictionary that contains the uploaded file(s)'s metadata.
    """
    files = {}
    # re_obj is a regular expression that specifies a set of strings and allows you to check if a particular string
    #   matches the regular expression. In this case, we are specifying 'filename_' and checking for it.
    re_obj = re.compile('filename_')
    for key in form.keys():
        if re_obj.match(key):
            files[key.split('filename_')[1]] = {}
    for key in files:
        re_obj = re.compile('^' + key + '::')
        for form_key in form.keys():
            if re_obj.match(form_key):
                files[key][form_key.split(key + '::')[1]] = form[form_key]
    return files


def process_email_template_request(request_id, data):
    """
    Process the email template for responses. Determine the type of response from passed in data and follows
    the appropriate execution path to render the email template.

    :param data: Data from the frontend AJAX call
    :param request_id: FOIL request ID

    :return: the HTML of the rendered template
    """
    page = urljoin(flask_request.host_url, url_for('request.view', request_id=request_id))
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    rtype = data['type']
    if rtype != "edit":
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], EMAIL_TEMPLATE_FOR_TYPE[data['type']])
    else:
        return _edit_email_handler(data)

    if rtype in determination_type.ALL:
        handler_for_type = {
            determination_type.EXTENSION: _extension_email_handler,
            determination_type.ACKNOWLEDGMENT: _acknowledgment_email_handler,
            determination_type.DENIAL: _denial_email_handler,
            determination_type.CLOSING: _closing_email_handler,
            determination_type.REOPENING: _reopening_email_handler
        }
    else:
        handler_for_type = {
            response_type.FILE: _file_email_handler,
            response_type.LINK: _link_email_handler,
            response_type.NOTE: _note_email_handler,
            response_type.INSTRUCTIONS: _instruction_email_handler,
            response_type.USER_REQUEST_ADDED: _user_request_added_email_handler,
            response_type.USER_REQUEST_EDITED: _user_request_edited_email_handler,
            response_type.USER_REQUEST_REMOVED: _user_request_removed_email_handler
        }
    return handler_for_type[rtype](request_id, data, page, agency_name, email_template)


def _acknowledgment_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for an acknowledgement.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of an acknowledgement
    """
    acknowledgment = data.get('acknowledgment')
    header = "The following will be emailed to the Requester:"

    if acknowledgment is not None:
        acknowledgment = json.loads(acknowledgment)
        default_content = True
        content = None
        date = _get_new_due_date(
            request_id,
            acknowledgment['days'],
            acknowledgment['date'],
            data['tz_name'])
        info = acknowledgment['info'].strip() or None
    else:
        default_content = False
        content = data['email_content']
        date = None
        info = None
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                date=date,
                                                info=info,
                                                page=page),
                    "header": header}), 200


def _denial_email_handler(request_id, data, page, agency_name, email_template):
    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        reasons=[Reasons.query.filter_by(id=reason_id).one().content
                 for reason_id in data.getlist('reason_ids[]')],
        agency_appeals_email=Requests.query.filter_by(id=request_id).one().agency.appeals_email,
        page=page
    )}), 200


def _closing_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for closing a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a closing
    """
    reasons = [Reasons.query.filter_by(id=reason_id).one().content
               for reason_id in data.getlist('reason_ids[]')]
    header = "The following will be emailed to the Requester:"
    if eval_request_bool(data['confirmation']):
        default_content = False
        content = data['email_content']
    else:
        default_content = True
        content = None
    return jsonify({"template": render_template(
        email_template,
        default_content=default_content,
        content=content,
        request_id=request_id,
        agency_name=agency_name,
        reasons=reasons,
        agency_appeals_email=Requests.query.filter_by(id=request_id).one().agency.appeals_email,
        page=page),
        "header": header}), 200


def _reopening_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for reopening a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered email template of a reopening
    """
    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        date=process_due_date(datetime.strptime(data['date'], '%Y-%m-%d'), data['tz_name']),
        page=page
    )}), 200


def _user_request_added_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for reopening a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered email template of a reopening
    """

    name = Users.query.filter_by(guid=data['guid']).first().name
    original_permissions = [int(i) for i in data.getlist('permission[]')]
    permissions = []
    for i, perm in enumerate(permission.ALL):
        if i in original_permissions:
            permissions.append(perm.label)

    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        added_permissions=permissions,
        name=name,
        page=page
    ), "name": name}), 200


def _user_request_edited_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for reopening a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered email template of a reopening
    """
    name = Users.query.filter_by(guid=data['guid']).first().name
    original_permissions = [int(i) for i in data.getlist('permission[]')]
    added_permissions = []
    removed_permissions = []
    for i, perm in enumerate(permission.ALL):
        if i in original_permissions:
            added_permissions.append(perm.label)
        else:
            removed_permissions.append(perm.label)

    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        added_permissions=added_permissions,
        removed_permissions=removed_permissions,
        name=name,
        admin=False,
        page=page
    ), "name": name}), 200


def _user_request_removed_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for reopening a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered email template of a reopening
    """

    name = Users.query.filter_by(guid=data['guid']).first().name
    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        page=page,
        name=name,
        admin=False
    ), "name": name}), 200


def _extension_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for an extension.
    Checks if dictionary of extension data exists. If not, renders the default response email template.
    If extension dictionary exists, renders the extension response template with provided arguments.

    :param request_id: FOIL request ID of the request being extended
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of an extension response
    """
    extension = data.get('extension')
    header = "The following will be emailed to the Requester:"
    # if data['extension'] exists, use email_content as template with specific extension email template
    if extension is not None:
        extension = json.loads(extension)
        default_content = True
        content = None
        # calculates new due date based on selected value if custom due date is not selected
        new_due_date = _get_new_due_date(
            request_id,
            extension['length'],
            extension['custom_due_date'],
            data['tz_name'])
        reason = extension['reason']
    # use default_content in response template
    else:
        default_content = False
        new_due_date = None
        reason = None
        content = data['email_content']
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                new_due_date=new_due_date,
                                                reason=reason,
                                                page=page),
                    "header": header}), 200


def _file_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for a file.
    Checks if dictionary of file data exists. If not, renders the default response email template.
    If file dictionary exists, renders the file response template with provided arguments.

    :param request_id: FOIL request ID of the request the file is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a file response
    """
    # create a dictionary of filenames to be passed through jinja to email template
    private_links = []
    release_public_links = []
    release_private_links = []

    release_date = None
    agency_default_email = None

    files = data.get('files')
    # if data['files'] exists, use email_content as template with specific file email template
    if files is not None:
        files = json.loads(files)
        default_content = True
        content = None
        header = "The following will be emailed to the Requester:"
        if eval_request_bool(data['is_private']):
            email_template = 'email_templates/email_private_file_upload.html'
            header = "The following will be emailed to all Assigned Users:"
        for file_ in files:
            file_link = {'filename': file_['filename'],
                         'title': file_['title'],
                         'link': '#'}
            if eval_request_bool(data['is_private']):
                private_links.append(file_link)
            elif file_.get('privacy') == RELEASE_AND_PUBLIC:
                release_public_links.append(file_link)
            elif file_.get('privacy') == RELEASE_AND_PRIVATE:
                release_private_links.append(file_link)
        if release_public_links or release_private_links:
            release_date = get_release_date(datetime.utcnow(),
                                            RELEASE_PUBLIC_DAYS,
                                            data.get('tz_name'))
            agency_default_email = Requests.query.filter_by(id=request_id).first().agency.default_email
    # use default_content in response template
    else:
        default_content = False
        header = None
        content = data['email_content']
    # iterate through files dictionary to create and append links of files with privacy option of not private
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                page=page,
                                                agency_name=agency_name,
                                                agency_default_email=agency_default_email,
                                                release_date=release_date,
                                                release_public_links=release_public_links,
                                                release_private_links=release_private_links,
                                                private_links=private_links),
                    "header": header}), 200


def _link_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for a link instruction.
    Checks if dictionary of link data exists and renders the default response email template.
    If link dictionary does not exist, use email_content from frontend to render confirmation.

    :param request_id: FOIL request ID of the request the file is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a file response
    """
    release_date = None
    link = data.get('link')
    # if data['link'] exists get instruction content and privacy, and render template accordingly
    if link is not None:
        link = json.loads(link)
        url = link['url']
        title = link['title']
        content = None
        privacy = link.get('privacy')
        if privacy == PRIVATE:
            header = "The following will be emailed to all Assigned Users:"
        else:
            header = "The following will be emailed to the Requester:"
            if privacy == RELEASE_AND_PUBLIC:
                release_date = get_release_date(datetime.utcnow(),
                                                RELEASE_PUBLIC_DAYS,
                                                data.get('tz_name'))
    # use email_content from frontend to render confirmation
    else:
        header = None
        url = None
        title = None
        privacy = None
        content = data['email_content']
    return jsonify({"template": render_template(email_template,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                url=url,
                                                title=title,
                                                page=page,
                                                release_date=release_date,
                                                privacy=privacy,
                                                response_privacy=response_privacy),
                    "header": header}), 200


def _note_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for note
    Checks if dictionary of note data exists and renders the default response email template.
    If note dictionary does not exist, use email_content from frontend to render confirmation.

    :param request_id: FOIL request ID of the request the note is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a note response
    """
    release_date = None
    note = data.get('note')
    if note is not None:
        note = json.loads(note)
        note_content = note['content']
        content = None
        privacy = note.get('privacy')
        # use private email template for note if privacy is private
        if privacy == PRIVATE:
            header = "The following will be emailed to all Assigned Users:"
        else:
            header = "The following will be emailed to the Requester:"
            if privacy == RELEASE_AND_PUBLIC:
                release_date = get_release_date(datetime.utcnow(),
                                                RELEASE_PUBLIC_DAYS,
                                                data.get('tz_name'))
    else:
        header = None
        note_content = None
        privacy = None
        content = data['email_content']
    return jsonify({"template": render_template(email_template,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                note_content=note_content,
                                                page=page,
                                                release_date=release_date,
                                                privacy=privacy,
                                                response_privacy=response_privacy),
                    "header": header}), 200


def _instruction_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for an offline instruction.
    Checks if dictionary of instruction data exists and renders the default response email template.
    If instruction dictionary does not exist, use email_content from frontend to render confirmation.

    :param request_id: FOIL request ID of the request the instruction is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of an instruction response
    """
    release_date = None
    instruction = data.get('instruction')
    # if data['instructions'] exists get instruction content and privacy, and render template accordingly
    if instruction is not None:
        instruction = json.loads(instruction)
        instruction_content = instruction['content']
        content = None
        privacy = instruction.get('privacy')
        if privacy == PRIVATE:
            header = "The following will be emailed to all Assigned Users:"
        else:
            header = "The following will be emailed to the Requester:"
            if privacy == RELEASE_AND_PUBLIC:
                release_date = get_release_date(datetime.utcnow(),
                                                RELEASE_PUBLIC_DAYS,
                                                data.get('tz_name'))
    # use email_content from frontend to render confirmation
    else:
        header = None
        instruction_content = None
        privacy = None
        content = data['email_content']
    return jsonify({"template": render_template(email_template,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                instruction_content=instruction_content,
                                                page=page,
                                                release_date=release_date,
                                                privacy=privacy,
                                                response_privacy=response_privacy),
                    "header": header}), 200


def _edit_email_handler(data):
    """
    Process email template for a editing a response.
    Checks if confirmation is true. If not, renders the default edit response email template.
    If confirmation is true, renders the edit response template with provided arguments.

    :param data: data from the frontend AJAX call

    :return: the HTML of the rendered template of an edited response
    """
    response_id = data['response_id']
    resp = Responses.query.filter_by(id=response_id, deleted=False).one()
    editor_for_type = {
        response_type.FILE: RespFileEditor,
        response_type.NOTE: RespNoteEditor,
        response_type.INSTRUCTIONS: RespInstructionsEditor,
        response_type.LINK: RespLinkEditor,
        # ...
    }
    editor = editor_for_type[resp.type](current_user, resp, flask_request, update=False)
    if editor.no_change:
        return jsonify({"error": "No changes detected."}), 200
    else:
        email_summary_requester, email_summary_edited, header = _get_edit_response_template(editor)

    # if confirmation is not empty and response type is not FILE, store email templates into redis
    if eval_request_bool(data.get('confirmation')) and resp.type != response_type.FILE:
        email_redis.set(get_email_key(response_id), email_summary_edited)
        if email_summary_requester is not None:
            email_redis.set(get_email_key(response_id, requester=True), email_summary_requester)
    return jsonify({
        "template": email_summary_requester or email_summary_edited,
        "header": header
    }), 200


def _get_edit_response_template(editor):
    """
    Get the email template(s) and header for confirmation page, for the edit response workflow, based on privacy options.

    :param editor: editor object from class ResponseEditor

    :return: email template for agency users.
             email template for requester if privacy is not private.
             header for confirmation page

    """
    header = None
    data = editor.flask_request.form
    agency_name = Requests.query.filter_by(id=editor.response.request.id).first().agency.name
    page = urljoin(flask_request.host_url, url_for('request.view', request_id=editor.response.request.id))
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], "email_edit_file.html") \
        if editor.response.type == response_type.FILE \
        else os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
    email_summary_requester = None
    release_and_viewable = data.get('privacy') != PRIVATE and editor.requester_viewable
    was_private = editor.data_old.get('privacy') == PRIVATE
    requester_content = None
    agency_content = None

    if eval_request_bool(data.get('confirmation')) or editor.update:
        default_content = False
        agency_content = data['email_content']

        if release_and_viewable or was_private:
            requester_content = data['email_content']
            agency_content = None

        if was_private:
            recipient = "the Requester"
        elif release_and_viewable:
            recipient = "all associated participants"
        else:
            recipient = "all Assigned Users"
        header = "The following will be emailed to {}:".format(recipient)
    else:
        if (data.get(
                'privacy') == PRIVATE or not editor.requester_viewable) and editor.response.type != response_type.FILE:
            email_template = 'email_templates/email_edit_private_response.html'
            default_content = None
        else:
            default_content = True

    # render email_template for requester if requester viewable keys are edited or privacy changed from private
    if release_and_viewable or was_private:
        email_summary_requester = render_template(email_template,
                                                  default_content=default_content,
                                                  content=requester_content,
                                                  request_id=editor.response.request.id,
                                                  agency_name=agency_name,
                                                  response=editor.response,
                                                  response_data=editor,
                                                  page=page,
                                                  privacy=data.get('privacy'),
                                                  response_privacy=response_privacy)
        default_content = True

    agency = True
    # email_summary_edited rendered every time for email that agency receives
    email_summary_edited = render_template(email_template,
                                           default_content=default_content,
                                           content=agency_content,
                                           request_id=editor.response.request.id,
                                           agency_name=agency_name,
                                           response=editor.response,
                                           response_data=editor,
                                           page=page,
                                           privacy=data.get('privacy'),
                                           response_privacy=response_privacy,
                                           agency=agency)
    return email_summary_requester, email_summary_edited, header


def get_email_key(response_id, requester=False):
    """
    Returns a formatted key for an email.
    Intended for storing the body of an email.

    :param response_id: id of the response
    :param requester: will the stored content be emailed to a requester?

    :return: the formatted key
        Ex.
            1_requester
            1_agency
    """
    return '_'.join((str(response_id), 'requester' if requester else 'agency'))


def get_file_links(response, release_public_links, release_private_links, private_links):
    """
    Create file links for a file response based on privacy.
    Append a file_link dictionary to either release_public_links, release_private_links, and private_links, based on
    privacy option.

    :param response: response object
    :param release_public_links: list of dictionaries of release and public files containing key and values of filename,
                                 title, and link to file
    :param release_private_links: list of dictionaries of release and public files containing key and values of
                                  filename, title, and link to file
    :param private_links: list of dictionaries of private files containing key and values of filename, title, and
                          link to file

    :return: list with appended file_link dictionary based on privacy
    """
    resp = Responses.query.filter_by(id=response.id).one()
    path = '/response/' + str(response.id)

    agency_link = urljoin(flask_request.url_root, path)
    if resp.privacy != PRIVATE:
        if resp.request.requester.is_anonymous_requester:
            resptoken = ResponseTokens(response.id)
            create_object(resptoken)
            params = urlencode({'token': resptoken.token})
            requester_url = urljoin(flask_request.url_root, path)
            requester_link = requester_url + "?%s" % params
        else:
            requester_link = urljoin(flask_request.url_root, path)
        file_link = {'filename': resp.name,
                     'title': resp.title,
                     'link': requester_link}
        if resp.privacy == RELEASE_AND_PUBLIC:
            release_public_links.append(file_link)
        else:
            release_private_links.append(file_link)
    else:
        file_link = {'filename': resp.name,
                     'title': resp.title,
                     'link': agency_link}
        private_links.append(file_link)
    return release_public_links, release_private_links, private_links


def send_file_email(request_id, release_public_links, release_private_links, private_links, email_content,
                    replace_string, tz_name):
    """
    Send email with file links detailing a file response has been added to the request.
    Requester receives email only if release_public_links and release_private_links list is not empty.
    Agency users are BCCed on the email the requester receives.
    Agency users receive a separate email if only private files were uploaded.

    :param request_id: FOIL request ID
    :param release_public_links: list of dictionaries of release and public files containing key and values of filename,
                                 title, and link to file
    :param release_private_links: list of dictionaries of release and public files containing key and values of
    filename, title, and link to file
    :param private_links: list of dictionaries of private files containing key and values of filename, title, and
                          link to file
    :param email_content: string body of email from tinymce textarea
    :param replace_string: alphanumeric random 32 character string to be replaced in email_content
    :param tz_name:

    """
    page = urljoin(flask_request.host_url, url_for('request.view', request_id=request_id))
    is_anon = Requests.query.filter_by(id=request_id).one().requester.is_anonymous_requester
    subject = 'Response Added to {} - File'.format(request_id)
    bcc = get_agency_emails(request_id)
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    requester_email = Requests.query.filter_by(id=request_id).one().requester.email
    if release_public_links or release_private_links:
        release_date = calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS)
        release_date = release_date + get_timezone_offset(release_date, tz_name)
        email_content_requester = email_content.replace(replace_string,
                                                        render_template('email_templates/response_file_links.html',
                                                                        release_public_links=release_public_links,
                                                                        release_private_links=release_private_links,
                                                                        is_anon=is_anon,
                                                                        release_date=release_date
                                                                        ))
        safely_send_and_add_email(request_id,
                                  email_content_requester,
                                  'Response Added to {} - File'.format(request_id),
                                  to=[requester_email],
                                  bcc=bcc)
        if private_links:
            email_content_agency = render_template('email_templates/email_private_file_upload.html',
                                                   request_id=request_id,
                                                   default_content=True,
                                                   agency_name=agency_name,
                                                   private_links=private_links,
                                                   page=page)
            safely_send_and_add_email(request_id,
                                      email_content_agency,
                                      'File(s) Added to {}'.format(request_id),
                                      bcc=bcc)
    else:
        email_content_agency = email_content.replace(replace_string,
                                                     render_template('email_templates/response_file_links.html',
                                                                     request_id=request_id,
                                                                     private_links=private_links,
                                                                     page=page
                                                                     ))
        safely_send_and_add_email(request_id,
                                  email_content_agency,
                                  subject,
                                  bcc=bcc)


def _send_edit_response_email(request_id, email_content_agency, email_content_requester=None):
    """
    Send email detailing a response has been edited.
    Always sends email to agency users on the request.
    Requester is emailed only if email_content_requester is provided.

    :param request_id: FOIL request ID
    :param email_content_agency: body of email being sent to agency users
    :param email_content_requester: body of email being sent to requester

    :type email_content_agency: str
    :type email_content_requester: str

    """
    subject = 'Response Edited'
    bcc = get_agency_emails(request_id)
    requester_email = Requests.query.filter_by(id=request_id).one().requester.email
    safely_send_and_add_email(request_id, email_content_agency, subject, bcc=bcc)
    if email_content_requester is not None:
        safely_send_and_add_email(request_id,
                                  email_content_requester,
                                  subject,
                                  to=[requester_email])


def _send_response_email(request_id, privacy, email_content, subject):
    """
    Function that sends email detailing a specific response has been added to a request.
    If the file privacy is private, only agency_ein users are emailed.
    If the file privacy is release, the requester is emailed and the agency_ein users are bcced.
    Call safely_send_and_add_email to send email notification detailing a specific response has been added to the
    request.

    :param request_id: FOIL request ID for the specific link
    :param email_content: content body of the email notification being sent
    :param privacy: privacy option of link

    """
    bcc = get_agency_emails(request_id)
    requester_email = Requests.query.filter_by(id=request_id).one().requester.email
    # Send email with link to requester and bcc agency_ein users as privacy option is release
    kwargs = {
        'bcc': bcc,
    }
    if privacy != PRIVATE:
        kwargs['to'] = [requester_email]
    safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              **kwargs)


def _send_delete_response_email(request_id, response):
    """
    Send an email notification to all agency users regarding
    a deleted response.

    """
    safely_send_and_add_email(
        request_id,
        render_template(
            'email_templates/email_response_deleted.html',
            request_id=request_id,
            response=response,
            response_type=response_type),
        'Response Deleted',
        to=get_agency_emails(request_id))


def safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              template=None,
                              to=None,
                              bcc=None,
                              **kwargs):
    """
    Send email based on given arguments and create and store email object into the Emails table.
    Print error messages if there is Assertion or Exception error occurs.

    :param request_id: FOIL request ID
    :param email_content: string of HTML email content that can be used as a message template
    :param subject: subject of the email (current is for TESTING purposes)
    :param template: path of the HTML template to be passed into and rendered in send_email
    :param to: list of person(s) email is being sent to
    :param bcc: list of person(s) email is being bcc'ed

    """
    try:
        send_email(subject, to=to, bcc=bcc, template=template, email_content=email_content, **kwargs)
        _add_email(request_id, subject, email_content, to=to, bcc=bcc)
    except AssertionError:
        print('Must include: To, CC, or BCC')
    except Exception as e:
        print("Error:", e)


def create_response_event(events_type, response):
    """
    Create and store event object for given response.

    :param response: response object
    :param events_type: one of app.constants.event_type

    """
    event = Events(request_id=response.request_id,
                   user_guid=current_user.guid,
                   auth_user_type=current_user.auth_user_type,
                   type_=events_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id,
                   new_value=response.val_for_events)
    # store event object
    create_object(event)


class ResponseEditor(metaclass=ABCMeta):
    """
    Abstract base class for editing a response.

    All derived classes must implement the 'editable_fields' method and
    should override the `set_edited_data` method with any additional logic.
    """

    def __init__(self, user, response, flask_request, update=True):
        self.user = user
        self.response = response
        self.flask_request = flask_request

        self.update = update
        self.no_change = False
        self.data_old = {}
        self.data_new = {}
        self.errors = []

        self.set_edited_data()
        if self.data_new and not self.errors:
            if update:
                self.add_event_and_update()
                self.send_email()
        else:
            self.no_change = True

    def set_data_values(self, key, old, new):
        if old != new:
            self.data_old[key] = old
            self.data_new[key] = new

    @property
    def event_type(self):
        return {
            Files: event_type.FILE_EDITED,
            Notes: event_type.NOTE_EDITED,
            Links: event_type.LINK_EDITED,
            Instructions: event_type.INSTRUCTIONS_EDITED,
        }[type(self.response)]

    @property
    @abstractmethod
    def editable_fields(self):
        """ List of fields that can be edited directly. """
        return list()

    @cached_property
    def requester_viewable_keys(self):
        """ List of keys for edited data that can be viewed by a requester. """
        viewable = dict(self.data_old)
        viewable.pop('privacy', None)
        return [k for k in viewable]

    @cached_property
    def requester_viewable(self):
        """ Can a requester view the changes made to the response? """
        return bool(self.requester_viewable_keys)

    def set_edited_data(self):
        """
        For the editable fields, populates the old and new data containers
        if the field values differ from their database counterparts.
        """
        for field in self.editable_fields + ['privacy', 'deleted']:
            value_new = self.flask_request.form.get(field)
            if value_new is not None:
                value_orig = str(getattr(self.response, field))
                if value_new != value_orig:
                    self.set_data_values(field, value_orig, value_new)
        if self.data_new.get('deleted') is not None:
            self.validate_deleted()

    def validate_deleted(self):
        """
        Removes the 'deleted' key-value pair from the data containers
        if the confirmation string (see response PATCH) is not valid.
        """
        confirmation = flask_request.form.get("confirmation")
        valid_confirmation_string = "DELETE"
        if confirmation is None or confirmation.upper() != valid_confirmation_string:
            self.data_old.pop('deleted')
            self.data_new.pop('deleted')

    def add_event_and_update(self):
        """
        Creates an 'edited' Event and updates the response record.
        """
        timestamp = datetime.utcnow()

        event = Events(
            type_=self.event_type,
            request_id=self.response.request_id,
            response_id=self.response.id,
            user_guid=self.user.guid,
            auth_user_type=self.user.auth_user_type,
            timestamp=timestamp,
            previous_value=self.data_old,
            new_value=self.data_new)
        create_object(event)

        data = dict(self.data_new)
        data['date_modified'] = timestamp
        if self.data_new.get('privacy') is not None:
            data['release_date'] = self.get_response_release_date()
        update_object(data,
                      type(self.response),
                      self.response.id)

    def get_response_release_date(self):
        return {
            response_privacy.RELEASE_AND_PUBLIC: calendar.addbusdays(
                datetime.utcnow(), RELEASE_PUBLIC_DAYS),
            response_privacy.RELEASE_AND_PRIVATE: None,
            response_privacy.PRIVATE: None,
        }[self.data_new.get('privacy')]

    @property
    def deleted(self):
        return self.data_new.get('deleted', False)

    def send_email(self):
        """
        Send an email to all relevant request participants.
        Email content varies according to which response fields have changed.
        """
        if self.deleted:
            _send_delete_response_email(self.response.request_id, self.response)
        else:
            key_agency = get_email_key(self.response.id)
            email_content_agency = email_redis.get(key_agency).decode()
            email_redis.delete(key_agency)

            key_requester = get_email_key(self.response.id, requester=True)
            email_content_requester = email_redis.get(key_requester)
            if email_content_requester is not None:
                email_content_requester = email_content_requester.decode()
                email_redis.delete(key_requester)

            _send_edit_response_email(self.response.request_id,
                                      email_content_agency,
                                      email_content_requester)


class RespFileEditor(ResponseEditor):
    @property
    def editable_fields(self):
        return ['title']

    def set_edited_data(self):
        """
        If the file itself is being edited, gather
        its metadata. The values of the 'size', 'name', 'mime_type',
        and 'hash' fields are determined by the new file.
        """
        super(RespFileEditor, self).set_edited_data()
        if self.deleted and self.update:
            self.move_deleted_file()
            if self.response.token is not None:
                delete_object(self.response.token)
        else:
            new_filename = flask_request.form.get('filename', '')
            if new_filename:
                new_filename = secure_filename(new_filename)
                filepath = os.path.join(
                    current_app.config['UPLOAD_DIRECTORY'],
                    self.response.request_id,
                    UPDATED_FILE_DIRNAME,
                    new_filename
                )
                if fu.exists(filepath):
                    try:
                        # fetch file metadata from redis store
                        size, mime_type, hash_ = redis_get_file_metadata(
                            self.response.id,
                            filepath,
                            is_update=True)
                    except AttributeError:
                        size = fu.getsize(filepath)
                        mime_type = fu.get_mime_type(filepath)
                        hash_ = fu.get_hash(filepath)
                    self.set_data_values('size',
                                         self.response.size,
                                         size)
                    self.set_data_values('name',
                                         self.response.name,
                                         new_filename)
                    self.set_data_values('mime_type',
                                         self.response.mime_type,
                                         mime_type)
                    self.set_data_values('hash',
                                         self.response.hash,
                                         hash_)
                    if self.update:
                        redis_delete_file_metadata(self.response.id, filepath, is_update=True)
                        self.replace_old_file(filepath)
                else:
                    self.errors.append(
                        "File '{}' not found.".format(new_filename))
            if self.update:
                self.handle_response_token(bool(new_filename))

    def replace_old_file(self, updated_filepath):
        """
        Move the new file out of the 'updated' directory
        and delete the file it is replacing.
        """
        upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.response.request_id
        )
        fu.remove(
            os.path.join(
                upload_path,
                self.response.name
            )
        )
        fu.rename(
            updated_filepath,
            os.path.join(
                upload_path,
                os.path.basename(updated_filepath)
            )
        )

    def handle_response_token(self, file_changed):
        """
        Handle the response token based on privacy option and if file has been replaced
        """
        if self.response.request.requester.is_anonymous_requester:
            # privacy changed to private
            if self.data_new.get('privacy') == PRIVATE:
                delete_object(self.response.token)
            # privacy changed from private or file was changed and the response is public
            elif self.data_old.get('privacy') == PRIVATE or (file_changed and self.response.privacy != PRIVATE):
                if not self.response.token:
                    # create new token
                    resptoken = ResponseTokens(self.response.id)
                    create_object(resptoken)
                else:
                    # extend expiration date
                    update_object(
                        {'expiration_date': calendar.addbusdays(datetime.utcnow(), DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS)},
                        ResponseTokens,
                        self.response.token.id
                    )

    @cached_property
    def file_link_for_user(self):
        """
        Get the link(s) of the file being edited.

        :return: dictionary with a nested dictionary, filename, with key of requester and agency and values of the
        respective file link(s).
        File link to the requester is not created if privacy is private.
        """
        file_links = dict()
        if self.update:
            path = '/response/' + str(self.response.id)
            if self.response.privacy != PRIVATE:
                if self.response.request.requester.is_anonymous_requester:
                    params = urlencode({'token': self.response.token.token})
                    requester_url = urljoin(flask_request.url_root, path)
                    requester_link = requester_url + "?%s" % params
                else:
                    requester_link = urljoin(flask_request.url_root, path)
                file_links['requester'] = requester_link
            agency_link = urljoin(flask_request.url_root, path)
            file_links['agency'] = agency_link
        else:
            file_links = {'requester': '#', 'agency': '#'}
        return file_links

    def send_email(self):
        """
        Send an email to all relevant request participants for editing a file.
        Email content varies according to which response fields have changed.
        """
        if self.deleted:
            _send_delete_response_email(self.response.request_id, self.response)
        else:
            email_content_requester, email_content_agency, _ = _get_edit_response_template(self)
            _send_edit_response_email(self.response.request_id,
                                      email_content_agency,
                                      email_content_requester)

    def move_deleted_file(self):
        """
        Move the file of a deleted response to the
        designated directory for deleted files.

        from:

            UPLOAD_DIRECTORY/<FOIL-ID>/

        to:

            UPLOAD_DIRECTORY/deleted/<response-ID>/

        """
        upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.response.request_id,
        )
        dir_deleted = os.path.join(
            upload_path,
            DELETED_FILE_DIRNAME,
            str(self.response.id)
        )
        if not fu.exists(dir_deleted):
            fu.makedirs(dir_deleted)
        fu.rename(
            os.path.join(
                upload_path,
                self.response.name
            ),
            os.path.join(
                dir_deleted,
                self.response.name
            )
        )


class RespNoteEditor(ResponseEditor):
    @property
    def editable_fields(self):
        return ['content']


class RespLinkEditor(ResponseEditor):
    @property
    def editable_fields(self):
        return ['title', 'url']


class RespInstructionsEditor(ResponseEditor):
    @property
    def editable_fields(self):
        return ['content']


class RespExtensionEditor(ResponseEditor):
    @property
    def editable_fields(self):
        return ['reason']
