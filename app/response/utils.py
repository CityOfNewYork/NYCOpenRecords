"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
import os
import re
import json
from datetime import datetime
from abc import ABCMeta, abstractmethod
import urllib.parse
from urllib.parse import urljoin

import magic
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
    user_type_auth,
    UPDATED_FILE_DIRNAME,
    DELETED_FILE_DIRNAME,
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PUBLIC
from app.lib.date_utils import generate_new_due_date
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import send_email, get_agency_emails
from app.lib.file_utils import get_mime_type
from app.lib.utils import (
    get_file_hash,
    eval_request_bool
)
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
    ResponseTokens
)


# TODO: class ResponseProducer()

def add_file(request_id, filename, title, privacy):
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
    size = os.path.getsize(path)
    mime_type = get_mime_type(request_id, filename)
    hash_ = get_file_hash(path)

    response = Files(
        request_id,
        privacy,
        title,
        filename,
        mime_type,
        size,
        hash_,
    )
    create_object(response)

    _create_response_event(response, event_type.FILE_ADDED)

    return response


def add_note(request_id, note_content, email_content, privacy):
    """
    Create and store the note object for the specified request.
    Store the note content into the Notes table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the note
    :param note_content: string content of the note to be created and stored as a note object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the note

    """
    response = Notes(request_id, privacy, note_content)
    create_object(response)
    _create_response_event(response, event_type.NOTE_ADDED)
    _send_response_email(request_id, privacy, email_content)


def add_acknowledgment(request_id, info, days, date, email_content):
    """
    Create and store an acknowledgement-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param info: additional information pertaining to the acknowledgment
    :param days: days until request completion
    :param date: date of request completion
    :param email_content: email body associated with the acknowledgment

    """
    if not Requests.query.filter_by(id=request_id).one().was_acknowledged:
        new_due_date = _get_new_due_date(request_id, days, date)
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
        _create_response_event(response, event_type.REQ_ACKNOWLEDGED)
        _send_response_email(request_id, privacy, email_content)


def add_denial(request_id, reason_ids, email_content):
    """
    Create and store a denial-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param reason: reason for denial
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
            ",".join(Reasons.query.filter_by(id=reason_id).one().content
                     for reason_id in reason_ids)
        )
        create_object(response)
        _create_response_event(response, event_type.REQ_CLOSED)  # FIXME: REQ_DENIED?
        _send_response_email(request_id, privacy, email_content)


def add_extension(request_id, length, reason, custom_due_date, email_content):
    """
    Create and store the extension object for the specified request.
    Extension's privacy is always Release and Public.
    Provides parameters for the process_response function to create and store responses and events object.
    Calls email notification function to email both requester and agency users detailing the extension.

    :param request_id: FOIL request ID for the extension
    :param length: length in business days that the request is being extended by
    :param reason: reason for the extension of the request
    :param custom_due_date: if custom_due_date is inputted from the frontend, the new extended date of the request
    :param email_content: email body content of the email to be created and stored as a email object

    """
    new_due_date = _get_new_due_date(request_id, length, custom_due_date)
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
    _create_response_event(response, event_type.REQ_EXTENDED)
    _send_response_email(request_id, privacy, email_content)


def add_link(request_id, title, url_link, email_content, privacy):
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
    response = Links(request_id, privacy, title, url_link)
    create_object(response)
    _create_response_event(response, event_type.LINK_ADDED)
    _send_response_email(request_id, privacy, email_content)


def add_instruction(request_id, instruction_content, email_content, privacy):
    """
    Creates and stores the instruction object for the specified request.
    Stores the instruction content into the Instructions table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the instruction
    :param instruction_content: string content of the instruction to be created and stored as a instruction object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the instruction

    """
    response = Instructions(request_id, privacy, instruction_content)
    create_object(response)
    _create_response_event(response, event_type.INSTRUCTIONS_ADDED)
    _send_response_email(request_id, privacy, email_content)


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
    to = ','.join([email.replace('{', '').replace('}', '') for email in to]) if to else None  # TODO: see why
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
    _create_response_event(response, event_type.EMAIL_NOTIFICATION_SENT)


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


def _get_new_due_date(request_id, extension_length, custom_due_date):
    """
    Gets the new due date from either generating with extension length, or setting from an inputted custom due date.
    If the extension length is -1, then we use the custom_due_date to determine the new_due_date.
    Or else, extension length has an length (20, 30, 60, 90, or 120) and new_due_date will be determined by
    generate_due_date.

    :param request_id: FOIL request ID that is being passed in to generate_new_due_date
    :param extension_length: length the due date is being extended by
    :param custom_due_date: new custom due date of the request

    :return: new_due_date of the request
    """
    if extension_length == '-1':
        new_due_date = datetime.strptime(custom_due_date, '%Y-%m-%d').replace(hour=17, minute=00, second=00)
    else:
        new_due_date = generate_new_due_date(extension_length, request_id)
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
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
    # set a dictionary of email types to handler functions to handle the specific response type

    rtype = data['type']
    if rtype in determination_type.ALL:
        handler_for_type = {
            determination_type.EXTENSION: _extension_email_handler,
            determination_type.ACKNOWLEDGMENT: _acknowledgment_email_handler,
            determination_type.DENIAL: _denial_email_handler,
        }
    else:
        handler_for_type = {
            response_type.FILE: _file_email_handler,
            response_type.LINK: _link_email_handler,
            response_type.NOTE: _note_email_handler,
            response_type.INSTRUCTIONS: _instruction_email_handler,
            "edit": _edit_email_handler
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

    if acknowledgment is not None:
        acknowledgment = json.loads(acknowledgment)
        default_content = False
        content = data['email_content']
        date = _get_new_due_date(
            request_id,
            acknowledgment['days'],
            acknowledgment['date']
        ).strftime('%A, %b, %d,%Y')
        info = acknowledgment['info'].strip() or None
    else:
        default_content = True
        content = None
        date = ''
        info = ''
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                date=date,
                                                info=info,
                                                page=page)}), 200


def _denial_email_handler(request_id, data, page, agency_name, email_template):
    return jsonify({"template": render_template(
        email_template,
        request_id=request_id,
        agency_name=agency_name,
        reasons=[Reasons.query.filter_by(id=reason_id).one().content
                 for reason_id in data.getlist('reason_ids[]')],
        page=page
    )}), 200


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
    # if data['extension'] exists, use email_content as template with specific extension email template
    if extension is not None:
        extension = json.loads(extension)
        default_content = False
        content = data['email_content']
        # calculates new due date based on selected value if custom due date is not selected
        new_due_date = _get_new_due_date(request_id,
                                         extension['length'],
                                         extension['custom_due_date']).strftime('%A, %b %d, %Y')
        reason = extension['reason']
    # use default_content in response template
    else:
        default_content = True
        content = None
        new_due_date = ''
        reason = ''
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                new_due_date=new_due_date,
                                                reason=reason,
                                                page=page)}), 200


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
    files_links = {}

    files = data.get('files')
    # if data['files'] exists, use email_content as template with specific file email template
    if files is not None:
        files = json.loads(files)
        default_content = False
        content = data['email_content']
    # use default_content in response template
    else:
        files = []
        default_content = True
        content = None
        if eval_request_bool(data['is_private']):
            email_template = 'email_templates/email_private_file_upload.html'
    # iterate through files dictionary to create and append links of files with privacy option of not private
    for file_ in files:
        if file_['privacy'] != PRIVATE or eval_request_bool(data['is_private']):
            filename = file_['filename']
            files_links[filename] = "http://127.0.0.1:5000/request/view/{}".format(filename)
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                page=page,
                                                agency_name=agency_name,
                                                files_links=files_links)}), 200


def _link_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for a link instruction.
    Checks if dictionary of link data exists. If not, renders the default response email template.
    If link dictionary exists, renders the link response template with provided arguments.

    :param request_id: FOIL request ID of the request the file is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a file response
    """
    link = data.get('link')
    # if data['link'] exists, use email_content as template with specific link email template
    if link is not None:
        link = json.loads(link)
        default_content = False
        content = data['email_content']
        url = link['url']
        privacy = link['privacy']
    # use default_content in response template
    else:
        url = ''
        content = None
        privacy = None
        if data['privacy'] == PRIVATE:
            email_template = 'email_templates/email_response_private_link.html'
            default_content = None
        else:
            default_content = True
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                url=url,
                                                page=page,
                                                privacy=privacy,
                                                response_privacy=response_privacy)}), 200


def _note_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for note
    Checks if dictionary of note data exists. If not, renders the default response email template.
    If note dictionary exists, renders the note response template with provided arguments.

    :param request_id: FOIL request ID of the request the note is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a note response
    """
    note = data.get('note')
    # if data['note'] exists, use email_content as template with specific link email template
    if note is not None:
        note = json.loads(note)
        default_content = False
        content = data['email_content']
        note_content = note['content']
        privacy = note['privacy']
    # use default_content in response template
    else:
        note_content = ''
        content = None
        privacy = None
        # use private email template for note if privacy is private
        if data['privacy'] == PRIVATE:
            email_template = 'email_templates/email_response_private_note.html'
            default_content = None
        else:
            default_content = True
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                note_content=note_content,
                                                page=page,
                                                privacy=privacy,
                                                response_privacy=response_privacy)}), 200


def _instruction_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for an offline instruction.
    Checks if dictionary of instruction data exists. If not, renders the default response email template.
    If instruction dictionary exists, renders the instruction response template with provided arguments.

    :param request_id: FOIL request ID of the request the instruction is being added to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of an instruction response
    """
    instruction = data.get('instruction')
    # if data['instructions'] exists, use email_content as template with specific instructions template
    if instruction is not None:
        instruction = json.loads(instruction)
        default_content = False
        content = data['email_content']
        instruction_content = instruction['content']
        privacy = instruction['privacy']
    # use default_content in response template
    else:
        instruction_content = ''
        content = None
        privacy = None
        if data['privacy'] == PRIVATE:
            email_template = 'email_templates/email_response_private_instruction.html'
            default_content = None
        else:
            default_content = True
    return jsonify({"template": render_template(email_template,
                                                default_content=default_content,
                                                content=content,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                instruction_content=instruction_content,
                                                page=page,
                                                privacy=privacy,
                                                response_privacy=response_privacy)}), 200


def _edit_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for a editing a response.
    Checks if confirmation is true. If not, renders the default edit response email template.
    If confirmation is true, renders the edit response template with provided arguments.

    :param request_id: FOIL request ID of the request the response is being edited to
    :param data: data from the frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the request
    :param email_template: raw HTML email template of the edit response

    :return: the HTML of the rendered template of an edited response
    """
    response_id = data['response_id']
    confirmation = eval_request_bool(data['confirmation'])
    privacy = data['privacy']
    email_summary_requester = None
    agency = False
    resp = Responses.query.filter_by(id=response_id, deleted=False).one()
    editor_for_type = {
        response_type.FILE: RespFileEditor,
        response_type.NOTE: RespNoteEditor,
        response_type.INSTRUCTIONS: RespInstructionsEditor,
        response_type.LINK: RespLinkEditor,
        # ...
    }
    editor = editor_for_type[resp.type](current_user, resp, flask_request, update=False)
    header = None
    if confirmation:
        default_content = False
        content = data['email_content']

        release_and_viewable = privacy != PRIVATE and editor.requester_viewable
        was_private = editor.data_old.get('privacy') == PRIVATE

        if release_and_viewable or was_private:
            email_summary_requester = render_template(email_template,
                                                      default_content=default_content,
                                                      content=content,
                                                      request_id=request_id,
                                                      agency_name=agency_name,
                                                      response=resp,
                                                      response_data=editor,
                                                      page=page,
                                                      privacy=privacy,
                                                      response_privacy=response_privacy)
        if release_and_viewable:
            recipient = "all associated participants"
        elif was_private:
            recipient = "the Requester"
        else:
            recipient = "all Assigned Users"
        header = "The following will be emailed to {}:".format(recipient)

        agency = True
    else:
        if editor.no_change:
            return jsonify({"error": "No changes detected."}), 200

        editor = None  # email_summary_edited template expects None
        content = None
        if privacy == PRIVATE:
            email_template = 'email_templates/email_edit_private_response.html'
            default_content = None
        else:
            default_content = True
    # email_summary_edited rendered every time for email that agency receives
    email_summary_edited = render_template(email_template,
                                           default_content=default_content,
                                           content=content,
                                           request_id=request_id,
                                           agency_name=agency_name,
                                           response=resp,
                                           response_data=editor,
                                           page=page,
                                           privacy=privacy,
                                           response_privacy=response_privacy,
                                           agency=agency)

    # if confirmation is true, store email templates into redis
    if confirmation:
        email_redis.set(get_email_key(response_id), email_summary_edited)
        if email_summary_requester is not None:
            email_redis.set(get_email_key(response_id, requester=True), email_summary_requester)
    return jsonify({
        "template": email_summary_requester or email_summary_edited,
        "header": header
    }), 200


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


def get_file_links(response, agency_file_links, requester_file_links):
    """
    Create file links for a file response based on privacy.
    Add file link item to agency_file_links dictionary and to requester_file_links dictionary if file response is not
    private.

    :param response: response object
    :param agency_file_links: dictionary of agency file links containing nested dictionaries of private and release
                              with both containing key, value of filename and file link
    :param requester_file_links: dictionary of file links to the requester with key, value of filename and file link

    :return: agency_file_links dictionary and requester_file_links (if file is not private) dictionary with
             added file link item
    """
    resp = Responses.query.filter_by(id=response.id).one()
    path = '/response/' + str(response.id)

    agency_link = urljoin(flask_request.url_root, path)
    if resp.privacy != PRIVATE:
        if resp.request.requester.is_anonymous_requester:
            resptoken = ResponseTokens(response.id)
            create_object(resptoken)
            params = urllib.parse.urlencode({'token': resptoken.token})
            requester_url = urljoin(flask_request.url_root, path)
            requester_link = requester_url + "?%s" % params
        else:
            requester_link = urljoin(flask_request.url_root, path)
        requester_file_links[resp.name] = requester_link
        agency_file_links['release'][resp.name] = agency_link
    else:
        agency_file_links['private'][resp.name] = agency_link
    return agency_file_links, requester_file_links


def send_file_email(request_id, agency_file_links, requester_file_links, email_content):
    """
    Send email with file links detailing a file response has been added to the request.
    Requester receives email only if requester_file_links dictionary has key and value.
    Agency users always receive email.

    :param request_id: FOIL request ID
    :param agency_file_links: dictionary of agency file links containing nested dictionaries of private and release
                              with both containing key, value of filename and file link
    :param requester_file_links: dictionary of file links to the requester with key, value of filename and file link
    :param email_content: string body of email from tinymce textarea

    :return:
    """
    page = urljoin(flask_request.host_url, url_for('request.view', request_id=request_id))
    is_anon = None
    if Requests.query.filter_by(id=request_id).one().requester.is_anonymous_requester:
        is_anon = True
    subject = 'Response Added'
    bcc = get_agency_emails(request_id)
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    requester_email = Requests.query.filter_by(id=request_id).one().requester.email
    if requester_file_links:
        email_content_requester = render_template('email_templates/email_response_file.html',
                                                  request_id=request_id,
                                                  email_file_content=email_content,
                                                  agency_name=agency_name,
                                                  requester_file_links=requester_file_links,
                                                  is_anon=is_anon)
        safely_send_and_add_email(request_id,
                                  email_content_requester,
                                  subject,
                                  to=[requester_email])
        email_content = None
    email_content_agency = render_template('email_templates/email_private_file_upload.html',
                                           request_id=request_id,
                                           email_file_content=email_content,
                                           agency_name=agency_name,
                                           agency_file_links=agency_file_links,
                                           page=page)
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

    :return:
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


def _send_response_email(request_id, privacy, email_content):
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
    subject = 'Response Added'
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


def _create_response_event(response, events_type):
    """
    Create and store event object for given response.

    :param response: response object
    :param events_type: one of app.constants.event_type

    """
    user = response.request.requester \
        if current_user.is_anonymous else current_user
    # FIXME: this is only for testing purposes, anonymous users cannot do anything with responses

    event = Events(request_id=response.request_id,
                   user_id=user.guid,
                   auth_user_type=user.auth_user_type,
                   type=events_type,
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
        valid_confirmation = ':'.join((self.response.request_id,
                                       str(self.response.id)))
        if confirmation is None or confirmation != valid_confirmation:
            self.data_old.pop('deleted')
            self.data_new.pop('deleted')

    def add_event_and_update(self):
        """
        Creates an 'edited' Event and updates the response record.
        """
        timestamp = datetime.utcnow()

        event = Events(
            type=self.event_type,
            request_id=self.response.request_id,
            response_id=self.response.id,
            user_id=self.user.guid,
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
        }[self.data_new['privacy']]


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
            # TODO: remove condition once edit File email handled, test will fail with this
            if self.response.type != response_type.FILE:
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
        else:
            new_filename = flask_request.form.get('filename')
            if new_filename is not None:
                new_filename = secure_filename(new_filename)
                filepath = os.path.join(
                    current_app.config['UPLOAD_DIRECTORY'],
                    self.response.request_id,
                    UPDATED_FILE_DIRNAME,
                    new_filename
                )
                if os.path.exists(filepath):
                    self.set_data_values('size',
                                         self.response.size,
                                         os.path.getsize(filepath))
                    self.set_data_values('name',
                                         self.response.name,
                                         new_filename)
                    self.set_data_values('mime_type',
                                         self.response.mime_type,
                                         magic.from_file(filepath, mime=True))
                    self.set_data_values('hash',
                                         self.response.hash,
                                         get_file_hash(filepath))
                    if self.update:
                        self.replace_old_file(filepath)
                else:
                    self.errors.append(
                        "File '{}' not found.".format(new_filename))

    def replace_old_file(self, updated_filepath):
        """
        Move the new file out of the 'updated' directory
        and delete the file it is replacing.
        """
        upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.response.request_id
        )
        os.remove(
            os.path.join(
                upload_path,
                self.response.name
            )
        )
        os.rename(
            updated_filepath,
            os.path.join(
                upload_path,
                os.path.basename(updated_filepath)
            )
        )

    def move_deleted_file(self):
        """
        Move the file to the 'deleted' directory
        and rename it to its hash.
        """
        upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.response.request_id,
        )
        dir_deleted = os.path.join(
            upload_path,
            DELETED_FILE_DIRNAME
        )
        if not os.path.exists(dir_deleted):
            os.mkdir(dir_deleted)
        os.rename(
            os.path.join(
                upload_path,
                self.response.name
            ),
            os.path.join(
                dir_deleted,
                self.response.hash
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
