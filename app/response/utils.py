"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
from datetime import datetime

import os
import re
import json
import magic
from abc import ABCMeta, abstractmethod
from cached_property import cached_property
from app import calendar
from werkzeug.utils import secure_filename
from flask_login import current_user
from flask import (
    current_app,
    request as flask_request,
    render_template,
    url_for
)
from app.constants import (
    event_type,
    response_type,
    UPDATED_FILE_DIRNAME,
    response_privacy,
)
from app.constants.user_type_auth import ANONYMOUS_USER
from app.constants.user_type_request import REQUESTER
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PUBLIC
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.lib.date_utils import generate_new_due_date
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import send_email, get_agencies_emails
from app.lib.file_utils import get_mime_type
from app.lib.utils import get_file_hash
from app.models import (
    Responses,
    Events,
    Notes,
    Files,
    Links,
    Instructions,
    Requests,
    UserRequests,
    Extensions,
    Emails
)


def add_file(request_id, filename, title, privacy):
    """
    Create and store the file object for the specified request.
    Gets the file mimetype and magic file check from a helper function in lib.file_utils
    File privacy options can be either Release and Public, Release and Private, or Private.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: Request ID that the file is being added to
    :param filename: The secured_filename of the file.
    :param title: The title of the file which is entered by the uploader.
    :param privacy: The privacy option of the file.

    :return:
    """
    path = os.path.join(current_app.config['UPLOAD_DIRECTORY'], request_id, filename)
    size = os.path.getsize(path)
    mime_type = get_mime_type(request_id, filename)
    file_ = Files(name=filename, mime_type=mime_type, title=title, size=size)
    file_metadata = {'name': filename,
                     'mime_type': mime_type,
                     'title': title,
                     'size': size,
                     'hash': get_file_hash(path)}
    create_object(obj=file_)
    _process_response(request_id,
                      response_type.FILE,
                      event_type.FILE_ADDED,
                      file_.id,
                      file_metadata,
                      privacy=privacy)


def delete_file():
    """
    Will delete a file in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a file
    print("delete_file function")

    return None


def add_note(request_id, note_content, email_content, privacy):
    """
    Create and store the note object for the specified request.
    Store the note content into the Notes table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the note
    :param note_content: string content of the note to be created and stored as a note object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the note

    :return:
    """
    note = Notes(content=note_content)
    create_object(obj=note)
    note_metadata = {'content': note_content,
                     'privacy': privacy}
    _process_response(request_id,
                      response_type.NOTE,
                      event_type.NOTE_ADDED,
                      note.id,
                      note_metadata,
                      privacy=privacy)
    _send_response_email(request_id,
                         privacy,
                         email_content)


def delete_note():
    """
    Will delete a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("delete_note function")


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

    :return:
    """
    new_due_date = _get_new_due_date(request_id, length, custom_due_date)
    update_object(
        {'due_date': new_due_date},
        Requests,
        request_id)
    extension = Extensions(reason=reason, date=new_due_date)
    create_object(obj=extension)
    privacy = RELEASE_AND_PUBLIC
    extension_metadata = {'reason': reason,
                          'date': new_due_date.isoformat(),
                          'privacy': privacy}
    _process_response(request_id,
                      response_type.EXTENSION,
                      event_type.REQ_EXTENDED,
                      extension.id,
                      extension_metadata,
                      privacy=privacy)
    _send_response_email(request_id,
                         privacy,
                         email_content)


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

    :return:
    """
    link = Links(title=title, url=url_link)
    create_object(obj=link)
    link_metadata = {'title': title,
                     'url': url_link,
                     'privacy': privacy}
    _process_response(request_id,
                      response_type.LINK,
                      event_type.LINK_ADDED,
                      link.id,
                      link_metadata,
                      privacy=privacy)
    _send_response_email(request_id,
                         privacy,
                         email_content)


def add_instruction(request_id, instruction_content, email_content, privacy):
    """
    Creates and stores the instruction object for the specified request.
    Stores the instruction content into the Instructions table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the instruction
    :param instruction_content: string content of the instruction to be created and stored as a instruction object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the instruction

    :return:
    """
    instruction = Instructions(content=instruction_content)
    create_object(obj=instruction)
    instruction_metadata = {'content': instruction_content,
                            'privacy': privacy}
    _process_response(request_id,
                      response_type.INSTRUCTIONS,
                      event_type.INSTRUCTIONS_ADDED,
                      instruction.id,
                      instruction_metadata,
                      privacy=privacy)
    _send_response_email(request_id,
                         privacy,
                         email_content)


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

    :return:
    """
    to = ','.join([email.replace('{', '').replace('}', '') for email in to]) if to else None
    cc = ','.join([email.replace('{', '').replace('}', '') for email in cc]) if cc else None
    bcc = ','.join([email.replace('{', '').replace('}', '') for email in bcc]) if bcc else None
    email = Emails(to=to, cc=cc, bcc=bcc, subject=subject, email_content=email_content)
    create_object(obj=email)
    email_content = {'email_content': email_content}
    _process_response(request_id,
                      response_type.EMAIL,
                      event_type.EMAIL_NOTIFICATION_SENT,
                      email.id,
                      new_value=email_content)


def add_sms():
    """
    Will add an SMS to the database for the specified request.
    :return:
    """
    # TODO: Implement adding an SMS
    print("add_sms function")


def add_push():
    """
    Will add a push to the database for the specified request.
    :return:
    """
    # TODO: Implement adding a push
    print("add_push function")


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


def process_privacy_options(files):
    """
    Create a dictionary, files_privacy_options, containing lists of 'release' and 'private', with values of filenames.
    Two empty lists: private_files and release_files are first created. Iterate through files dictionary to determine
    the privacy options of file(s) and append to appropriate list. Create files_privacy_option dictionary with keys:
    release, which holds release_files, and private, which holds private_files.

    :param files: list of filenames

    :return: Dictionary with 'release' and 'private' lists.
    """
    private_files = []
    release_files = []
    for filename in files:
        if files[filename]['privacy'] == 'private':
            private_files.append(filename)
        else:
            release_files.append(filename)

    files_privacy_options = dict()

    if release_files:
        files_privacy_options['release'] = release_files

    if private_files:
        files_privacy_options['private'] = private_files
    return files_privacy_options


def process_email_template_request(request_id, data):
    """
    Process the email template for responses. Determine the type of response from passed in data and follows
    the appropriate execution path to render the email template.

    :param data: Data from the frontend AJAX call
    :param request_id: FOIL request ID

    :return: the HTML of the rendered template
    """
    page = flask_request.host_url.strip('/') + url_for('request.view', request_id=request_id)
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
    # set a dictionary of email types to handler functions to handle the specific response type
    handler_for_type = {
        response_type.EXTENSION: _extension_email_handler,
        response_type.FILE: _file_email_handler,
        response_type.LINK: _link_email_handler,
        response_type.NOTE: _note_email_handler,
        response_type.INSTRUCTIONS: _instruction_email_handler
    }
    return handler_for_type[data['type']](request_id, data, page, agency_name, email_template)


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
    return render_template(email_template,
                           default_content=default_content,
                           content=content,
                           request_id=request_id,
                           agency_name=agency_name,
                           new_due_date=new_due_date,
                           reason=reason,
                           page=page)


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
    # iterate through files dictionary to create and append links of files with privacy option of not private
    for file_ in files:
        if file_['privacy'] != PRIVATE:
            filename = file_['filename']
            files_links[filename] = "http://127.0.0.1:5000/request/view/{}".format(filename)
    return render_template(email_template,
                           default_content=default_content,
                           content=content,
                           request_id=request_id,
                           page=page,
                           agency_name=agency_name,
                           files_links=files_links)


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
    return render_template(email_template,
                           default_content=default_content,
                           content=content,
                           request_id=request_id,
                           agency_name=agency_name,
                           url=url,
                           page=page,
                           privacy=privacy,
                           response_privacy=response_privacy)


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
    return render_template(email_template,
                           default_content=default_content,
                           content=content,
                           request_id=request_id,
                           agency_name=agency_name,
                           note_content=note_content,
                           page=page,
                           privacy=privacy,
                           response_privacy=response_privacy)


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
    return render_template(email_template,
                           default_content=default_content,
                           content=content,
                           request_id=request_id,
                           agency_name=agency_name,
                           instruction_content=instruction_content,
                           page=page,
                           privacy=privacy,
                           response_privacy=response_privacy)


def send_file_email(request_id, privacy, filenames, email_content, **kwargs):
    """
    Function that sends email detailing a file response has been uploaded to a request.
    If the file privacy is private, only agency_ein users are emailed.
    If the file privacy is release, the requester is emailed and the agency_ein users are bcced.
    Send email notification detailing a file response has been uploaded to the request.

    :param request_id: FOIL request ID
    :param privacy: privacy option of the uploaded file
    :param filenames: list of secured filenames
    :param email_content: string of HTML email content that can be used as a message template

    :return:

    """
    # TODO: make subject constants
    subject = 'Response Added'
    bcc = get_agencies_emails(request_id)
    # create a dictionary of filenames to be passed through jinja to email template
    file_to_link = {}
    for filename in filenames:
        file_to_link[filename] = "http://127.0.0.1:5000/request/view/{}".format(filename)
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    if privacy == 'release':
        # Query for the requester's email information
        requester_email = UserRequests.query.filter_by(request_id=request_id,
                                                       request_user_type=REQUESTER).first().user.email
        # Send email with files to requester and bcc agency_ein users as privacy option is release
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  to=[requester_email],
                                  bcc=bcc,
                                  agency_name=agency_name,
                                  files_links=file_to_link)

    if privacy == 'private':
        # Send email with files to agency_ein users only as privacy option is private
        email_content = render_template(kwargs['email_template'],
                                        request_id=request_id,
                                        agency_name=agency_name,
                                        files_links=file_to_link)
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  bcc=bcc)


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

    :return:
    """
    subject = 'Response Added'
    bcc = get_agencies_emails(request_id)
    requester_email = UserRequests.query.filter_by(request_id=request_id,
                                                   request_user_type=REQUESTER).first().user.email
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

    :return:
    """
    try:
        send_email(subject, to=to, bcc=bcc, template=template, email_content=email_content, **kwargs)
        _add_email(request_id, subject, email_content, to=to, bcc=bcc)
    except AssertionError:
        print('Must include: To, CC, or BCC')
    except Exception as e:
        print("Error:", e)


def _process_response(request_id,
                      responses_type,
                      events_type,
                      metadata_id,
                      new_value,
                      previous_value=None,
                      privacy=PRIVATE):
    """
    Create and store response object with given arguments from separate response type functions to the database.
    Calculates response release_date (20 business days from today) if privacy option is release and public.
    Check and determine user type for event object as per request.
    Create and store events object to the database.

    :param request_id: FOIL request ID to be stored into the responses and events tables
    :param responses_type: type of response to be stored in the responses table
    :param events_type: type of event to be stored in the events table
    :param metadata_id: metadata_id of the specific response to be stored in the responses table
    :param privacy: privacy of the response (default is 'private') to be stored in the responses table
    :param new_value: string content of the new response, to be stored in the responses table
    :param previous_value: string content of the previous response, to be stored in the responses table

    :return:
    """
    # calculate response release_date (20 business days from today) if privacy is release and public
    release_date = calendar.addbusdays(datetime.now(), RELEASE_PUBLIC_DAYS) if privacy == RELEASE_AND_PUBLIC else None

    # create response object
    response = Responses(request_id,
                         responses_type,
                         metadata_id,
                         privacy,
                         datetime.utcnow(),
                         release_date)
    # store response object
    create_object(obj=response)

    if current_user.is_anonymous:
        user_guid = UserRequests.query.with_entities(UserRequests.user_guid).filter_by(request_id=request_id,
                                                                                       request_user_type=REQUESTER)[0]
        auth_user_type = ANONYMOUS_USER
    else:
        user_guid = current_user.guid
        auth_user_type = current_user.auth_user_type

    new_value.update(privacy=privacy)
    event = Events(request_id=request_id,
                   user_id=user_guid,
                   auth_user_type=auth_user_type,
                   type=events_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id,
                   previous_value=previous_value,
                   new_value=new_value)
    # store event object
    create_object(obj=event)


class ResponseEditor(metaclass=ABCMeta):
    """
    Abstract base class for editing a response and its metadata.

    All derived classes must implement the 'metadata_fields' method and
    should override the `edit_metadata` method with any additional logic.
    """

    def __init__(self, user, response, flask_request):
        self.user = user
        self.response = response
        self.flask_request = flask_request
        self.metadata = response.metadatas

        self.no_change = False
        self.data_old = {}
        self.data_new = {}
        self.errors = []

        self.privacy_changed = False
        privacy = flask_request.form.get('privacy')
        if privacy is not None and privacy != self.response.privacy:
            self.set_data_values('privacy', self.response.privacy, privacy)
            self.privacy_changed = True

        self.edit_metadata()
        if self.data_changed():
            self.add_event_and_update()
        else:
            self.no_change = True

        # TODO: self.email()
        # What should be the email_content?
        # Edit existing email response OR new response?
        # EMAIL_NOTIFICATION_SENT + EMAIL_EDITED?

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
            Instructions: event_type.INSTRUCTIONS_ADDED,
        }[type(self.metadata)]

    @cached_property
    def metadata_new(self):
        if 'privacy' in self.data_new:
            data = dict(self.data_new)
            data.pop('privacy')
            return data
        return self.data_new

    @property
    @abstractmethod
    def metadata_fields(self):
        """ List of fields that can be edited directly. """
        return list()

    def edit_metadata(self):
        """
        For the editable fields, populates the
        old and new data containers.
        """
        for field in self.metadata_fields:
            value_new = self.flask_request.form.get(field)
            value_orig = getattr(self.metadata, field)
            if value_new is not None:
                self.set_data_values(field, value_orig, value_new)

    def data_changed(self):
        """
        Checks for a difference between new data values and their
        corresponding database fields.

        :returns: is the data different from what is stored in the db?
        """
        if self.privacy_changed:
            return True
        for key, value in self.metadata_new.items():
            if value != getattr(self.metadata, key):
                return True
        return False

    def add_event_and_update(self):
        """
        Creates an 'edited' event and updates the
        response and metadata records.
        """
        if not self.errors:
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
            response_changes = {
                'date_modified': timestamp
            }
            if self.privacy_changed:
                response_changes.update(
                    privacy=self.data_new['privacy']
                )
            update_object(response_changes,
                          Responses,
                          self.response.id)
            if self.metadata_new:
                update_object(self.metadata_new,
                              type(self.metadata),
                              self.metadata.id)


class RespFileEditor(ResponseEditor):
    @property
    def metadata_fields(self):
        return ['title']

    def edit_metadata(self):
        """
        If the file itself is being edited, gathers
        its metadata. The values of the 'size', 'name', and
        'mimetype' fields are determined by the new file.
        """
        super(RespFileEditor, self).edit_metadata()
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
                                     self.metadata.size,
                                     os.path.getsize(filepath))
                self.set_data_values('name',
                                     self.metadata.name,
                                     new_filename)
                self.set_data_values('mime_type',
                                     self.metadata.mime_type,
                                     magic.from_file(filepath, mime=True))
                self.set_data_values('hash',
                                     self.metadata.hash,
                                     get_file_hash(filepath))
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
                self.metadata.name
            )
        )
        os.rename(
            updated_filepath,
            os.path.join(
                upload_path,
                os.path.basename(updated_filepath)
            )
        )


class RespNoteEditor(ResponseEditor):
    @property
    def metadata_fields(self):
        return ['content']


class RespLinkEditor(ResponseEditor):
    @property
    def metadata_fields(self):
        return ['title', 'url']


class RespInstructionsEditor(ResponseEditor):
    @property
    def metadata_fields(self):
        return ['content']


class RespExtensionEditor(ResponseEditor):
    @property
    def metadata_fields(self):
        return ['reason']
