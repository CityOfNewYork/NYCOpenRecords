"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
from datetime import datetime

import os
import re
from abc import ABCMeta, abstractmethod
import magic
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
)
from app.constants.user_type_auth import ANONYMOUS_USER
from app.constants.user_type_request import REQUESTER
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PUBLIC
from app.lib.date_utils import generate_new_due_date
from app.lib.db_utils import create_object, update_object
from app.lib.email_utils import send_email, get_agencies_emails
from app.lib.file_utils import get_mime_type
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
    Creates and stores the file object for the specified request.
    Gets the file mimetype from a helper function in lib.file_utils

    :param request_id: Request ID that the file is being added to
    :param filename: The secured_filename of the file.
    :param title: The title of the file which is entered by the uploader.
    :param privacy: The privacy option of the file.

    :return: Stores the file metadata into the Files table.
             Provides parameters for the process_response function to create and store responses and events object.
    """
    size = os.path.getsize(os.path.join(current_app.config['UPLOAD_DIRECTORY'] + request_id, filename))
    mime_type = get_mime_type(request_id, filename)
    file_ = Files(name=filename, mime_type=mime_type, title=title, size=size)
    file_metadata = {'name': filename,
                     'mime_type': mime_type,
                     'title': title,
                     'size': size}
    create_object(obj=file_)
    _process_response(request_id,
                      response_type.FILE,
                      event_type.FILE_ADDED,
                      file_.id,
                      new_response_value=file_metadata,
                      privacy=privacy)


def delete_file():
    """
    Will delete a file in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a file
    print("delete_file function")

    return None


def add_note(request_id, content):
    """
    Creates and stores the note object for the specified request.

    :param request_id: takes in FOIL request ID as an argument for the process_response function
    :param content: content of the note to be created and stored as a note object

    :return: Stores the note content into the Notes table.
             Provides parameters for the process_response function to create and store responses and events object.
    """
    note = Notes(content=content)
    create_object(obj=note)
    content = {'content': content}
    _process_response(request_id,
                      response_type.NOTE,
                      event_type.NOTE_ADDED,
                      note.id,
                      new_response_value=content)


def delete_note():
    """
    Will delete a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("delete_note function")


def add_extension(request_id, length, reason, custom_due_date, email_content):
    new_due_date = _get_new_due_date(request_id, length, custom_due_date)
    update_object(
        {'due_date': new_due_date},
        Requests,
        request_id)
    extension = Extensions(reason=reason, date=new_due_date)
    create_object(obj=extension)
    extension_metadata = {'reason': reason,
                          'date': new_due_date.isoformat()}
    _process_response(request_id,
                      response_type.EXTENSION,
                      event_type.REQ_EXTENDED,
                      extension.id,
                      new_response_value=extension_metadata,
                      privacy=RELEASE_AND_PUBLIC)
    send_extension_email(request_id,
                         new_due_date,
                         reason,
                         email_content)


def _get_new_due_date(request_id, extension_length, custom_due_date):
    """
    Gets the new due date from either generating with extension length, or setting from an inputted custom due date.
    If the extension length is -1, then we use the custom_due_date to determine the new_due_date.
    Or else, extension length has an length (20, 30, 60, 90, or 120) and new_due_date will be determined by
    generate_due_date.

    :param request_id: FOIL request ID that is being
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
    Creates and stores the email object for the specified request.

    :param request_id: takes in FOIL request ID as an argument for the process_response function
    :param subject: subject of the email to be created and stored as a email object
    :param email_content: string of HTML email content to be created and stored as a email object
    :param to: list of person(s) email is being sent to
    :param cc: list of person(s) email is being cc'ed to
    :param bcc: list of person(s) email is being bcc'ed
    :return: Stores the email metadata into the Emails table.
             Provides parameters for the process_response function to create and store responses and events object.
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
                      new_response_value=email_content)


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

    :return: A files dictionary that contains the uploaded file(s)'s metadata that will be passed as arguments to be
     stored in the database.
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


def send_file_email(request_id, privacy, filenames, email_content):
    """
    Function that sends email detailing a file response has been uploaded to a request.
    If the file privacy is private, only agency users are emailed.
    If the file privacy is release, the requester is emailed and the agency users are bcced.

    :param request_id: FOIL request ID
    :param privacy: privacy option of the uploaded file
    :param filenames: list of filenames
    :param email_content: content body of the email notification being sent
    :return: Sends email notification detailing a file response has been uploaded to a request.

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
        # Send email with files to requester and bcc agency users as privacy option is release
        to = [requester_email]
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  "email_templates/email_file_upload",
                                  to=to,
                                  bcc=bcc,
                                  agency_name=agency_name,
                                  files_links=file_to_link)

    if privacy == 'private':
        # Send email with files to agency users only as privacy option is private
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  "email_templates/email_file_upload",
                                  bcc=bcc,
                                  agency_name=agency_name,
                                  files_links=file_to_link)


def process_privacy_options(files):
    """
    Creates a dictionary, files_privacy_options, containing lists of 'release' and 'private', with values of filenames.

    :param files: list of filenames
    :return: Dictionary with 'release' and 'private' lists
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
    :return: Renders email template with its given arguments
    """
    page = flask_request.host_url.strip('/') + url_for('request.view', request_id=request_id)
    agency_name = Requests.query.filter_by(id=request_id).first().agency.name
    # process email template for extension
    if data['type'] == 'extension_email':
        # calculates new due date based on selected value if custom due date is not selected
        new_due_date = _get_new_due_date(request_id,
                                         data['extension_length'],
                                         data['custom_due_date']).strftime('%A, %b %d, %Y')
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
        return render_template(email_template,
                               data=data,
                               new_due_date=new_due_date,
                               reason=data['extension_reason'],
                               page=page)
    # process email template for file upload
    if data['type'] == 'file_upload_email':
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
        # create a dictionary of filenames to be passed through jinja to email template
        files_links = {}
        try:
            files = data['files']
        except KeyError:
            files = []
        for file_ in files:
            if file_['privacy'] != PRIVATE:
                filename = file_['filename']
                files_links[filename] = "http://127.0.0.1:5000/request/view/{}".format(filename)
        return render_template(email_template,
                               data=data,
                               page=page,
                               agency_name=agency_name,
                               files_links=files_links)


def send_file_email(request_id, privacy, filenames, email_content, **kwargs):
    """
    Function that sends email detailing a file response has been uploaded to a request.
    If the file privacy is private, only agency_ein users are emailed.
    If the file privacy is release, the requester is emailed and the agency_ein users are bcced.

    :param request_id: FOIL request ID
    :param privacy: privacy option of the uploaded file
    :param filenames: list of secured filenames
    :param email_content: string of HTML email content that can be used as a message template
    :return: Sends email notification detailing a file response has been uploaded to a request.

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
        to = [requester_email]
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  to=to,
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


def send_extension_email(request_id, new_due_date, reason, email_content):
    """
    Function that sends email detailing a extension has been added to a request.

    :param request_id: FOIL request ID
    :param new_due_date: extended due date of the request
    :param reason: reason for extending the request
    :param email_content: string of HTML email content that can be used as a message template

    :return: An email is sent to the requester and all agency users are bcc detailing an extension has been added to a
    request.
    """
    subject = 'Response Added'
    bcc = get_agencies_emails(request_id)
    requester_email = UserRequests.query.filter_by(request_id=request_id,
                                                   request_user_type=REQUESTER).first().user.email
    # Send email with files to requester and bcc agency users as privacy option is release
    to = [requester_email]
    safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              to=to,
                              bcc=bcc,
                              new_due_date=new_due_date.strftime('%A, %b %d, %Y'),
                              reason=reason)


def safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              template=None,
                              to=None,
                              bcc=None,
                              **kwargs):
    """
    Sends email and creates and stores the email object into the Emails table.

    :param request_id: FOIL request ID
    :param email_content: string of HTML email content that can be used as a message template
    :param subject: subject of the email (current is for TESTING purposes)
    :param template: path of the HTML template to be passed into and rendered in send_email
    :param to: list of person(s) email is being sent to
    :param bcc: list of person(s) email is being bcc'ed

    :return: Sends email based on given arguments and creates and stores email object into the Emails table.
             Will print error if there is an error.
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
                      new_response_value,
                      previous_response_value=None,
                      privacy=PRIVATE):
    """
    Creates and stores responses and events objects to the database

    :param request_id: FOIL request ID to be stored into the responses and events tables
    :param responses_type: type of response to be stored in the responses table
    :param events_type: type of event to be stored in the events table
    :param metadata_id: metadata_id of the specific response to be stored in the responses table
    :param privacy: privacy of the response (default is 'private') to be stored in the responses table
    :param new_response_value: string content of the new response, to be stored in the responses table
    :param previous_response_value: string content of the previous response, to be stored in the responses table
    :return: Creates and stores response object with given arguments from separate response type functions.
             Creates and stores events object to the database.
    """
    # create response object
    response = Responses(request_id=request_id,
                         type=responses_type,
                         date_modified=datetime.utcnow(),
                         metadata_id=metadata_id,
                         privacy=privacy)
    # store response object
    create_object(obj=response)

    if current_user.is_anonymous:
        user_guid = UserRequests.query.with_entities(UserRequests.user_guid).filter_by(request_id=request_id,
                                                                                       request_user_type=REQUESTER)[0]
        auth_user_type = ANONYMOUS_USER
    else:
        user_guid = current_user.guid
        auth_user_type = current_user.auth_user_type

    event = Events(request_id=request_id,
                   user_id=user_guid,
                   auth_user_type=auth_user_type,
                   type=events_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id,
                   previous_response_value=previous_response_value,
                   new_response_value=new_response_value.update(privacy=privacy))
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

        self.data_old = {}
        self.data_new = {}
        self.errors = []

        privacy = flask_request.form.get('privacy')
        if privacy and privacy != self.response.privacy:
            self.set_data_values('privacy', self.response.privacy, privacy)

        self.edit_metadata()
        self.add_event_and_update()
        # TODO: self.email()
        # What should be the email_content?
        # Edit existing email response OR new response?
        # EMAIL_NOTIFICATION_SENT + EMAIL_EDITED?

    def set_data_values(self, key, old, new):
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

    @property
    def metadata_new(self):
        data = dict(self.data_new)
        data.pop('privacy')
        return data

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
            if value_new and value_new != value_orig:
                self.set_data_values(field, value_orig, value_new)

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
                previous_response_value=self.data_old,
                new_response_value=self.data_new)
            create_object(event)
            update_object({'date_modified': timestamp,
                          'privacy': self.data_new['privacy']},
                          Responses,
                          self.response.id)
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
