"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
from datetime import datetime

import os
import re
from flask import current_app, request as flask_request, render_template, url_for
from flask_login import current_user

from app.constants import (
    event_type,
    response_type,
    ANONYMOUS_USER
)
from app.constants.request_user_type import REQUESTER
from app.lib.db_utils import create_object, date_deserialize
from app.lib.email_utils import send_email, get_agencies_emails
from app.lib.date_utils import get_new_due_date
from app.lib.file_utils import get_mime_type
from app.models import (
    Responses,
    Events,
    Notes,
    Files,
    UserRequests,
    Requests,
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
    files = Files(name=filename, mime_type=mime_type, title=title, size=size)
    files_metadata = {'name': filename,
                      'mime_type': mime_type,
                      'title': title,
                      'size': size}
    create_object(obj=files)
    _process_response(request_id,
                      response_type.FILE,
                      event_type.FILE_ADDED,
                      files.metadata_id,
                      new_response_value=files_metadata,
                      privacy=privacy)


def delete_file():
    """
    Will delete a file in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a file
    print("delete_file function")

    return None


def edit_file():
    """
    Will edit a file to the database for the specified request.
    :return:
    """
    # TODO: Implement editing a file
    print("edit_file function")


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
                      note.metadata_id,
                      new_response_value=content)


def delete_note():
    """
    Will delete a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("delete_note function")


def edit_note():
    """
    Will edit a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("edit_note function")


def add_extension(request_id, extension_length, reason, custom_due_date, email_content):
    """
    Creates and stores the extension object for the specified request.

    :param request_id: Request ID that the extension is being added to
    :param extension_length: length the due date is being extended by
    :param reason: reason for extending the request
    :param custom_due_date: new custom due date of the request
    :param email_content: email body content of the email to be created and stored as a email object
    :return: Stores the extension metadata (reason and new due date) into the Extensions table.
             Provides parameters for the process_response function to create and store responses and events object.
             Privacy for an extension is always release and public.
    """
    if extension_length == '-1':
        new_due_date = datetime.strptime(custom_due_date, '%Y-%m-%d').replace(hour=17, minute=00, second=00)
    else:
        new_due_date = get_new_due_date(extension_length, request_id)
    extension = Extensions(reason=reason, date=new_due_date)
    create_object(obj=extension)
    extension_metadata = {'reason': reason,
                          'date': date_deserialize(new_due_date)}
    _process_response(request_id,
                      response_type.EXTENSION,
                      event_type.REQ_EXTENDED,
                      extension.metadata_id,
                      new_response_value=extension_metadata,
                      privacy='release_public')
    send_extension_email(request_id,
                         new_due_date,
                         reason,
                         email_content)


def edit_extension():
    """
    Will edit an extension to the database for the specified request.
    :return:
    """
    # TODO: Implement editing an extension
    print("edit_extension function")


def _add_email(request_id, subject, email_content, to=None, cc=None, bcc=None):
    """
    Creates and stores the note object for the specified request.

    :param request_id: takes in FOIL request ID as an argument for the process_response function
    :param subject: subject of the email to be created and stored as a email object
    :param email_content: email body content of the email to be created and stored as a email object
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
                      email.metadata_id,
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
        re_obj = re.compile(key)
        for form_key in form.keys():
            if re_obj.match(form_key):
                files[key][form_key.split(key + '::')[1]] = form[form_key]
    return files


def send_file_email(request_id, privacy, filenames, email_content):
    """
    Function that sends email detailing a file response has been uploaded to a request.
    If the file privacy is private, only agency_ein users are emailed.
    If the file privacy is release, the requester is emailed and the agency_ein users are bcced.

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

    if privacy == 'release':
        # Query for the requester's email information
        # Query for the requester's guid from UserRequests using first because there can only be one unique requester
        requester_email = UserRequests.query.filter_by(request_id=request_id,
                                                       request_user_type=REQUESTER).first().user.email

        # Send email with files to requester and bcc agency_ein users as privacy option is release
        to = [requester_email]
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  "email_templates/email_file_upload",
                                  to=to,
                                  bcc=bcc,
                                  agency_name="Department of Records and Information Services",
                                  files_links=file_to_link)

    if privacy == 'private':
        # Send email with files to agency_ein users only as privacy option is private
        safely_send_and_add_email(request_id,
                                  email_content,
                                  subject,
                                  "email_templates/email_file_upload",
                                  bcc=bcc,
                                  agency_name="Department of Records and Information Services",
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
    Processes the email template for responses. From data, determine the type of response and follow the appropriate
    execution path to render the email template.

    :param data: Data from the frontend AJAX call
    :param request_id: FOIL request ID
    :return: Renders email template with its given arguments
    """
    page = flask_request.host_url.strip('/') + url_for('request.view', request_id=request_id)
    # process email template for extension
    if data['type'] == 'extension_email':
        # calculates new due date based on selected value if custom due date is not selected
        if data['extension_length'] != "-1":
            new_due_date = get_new_due_date(data['extension_length'], request_id).strftime('%A, %b %d, %Y')
        else:
            new_due_date = datetime.strptime(data['custom_due_date'], '%Y-%m-%d').replace(hour=17, minute=00, second=00).strftime('%A, %b %d, %Y')
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
        return render_template(email_template,
                               data=data,
                               new_due_date=new_due_date,
                               reason=data['extension_reason'],
                               page=page)
    # process email template for file upload
    if data['type'] == 'file_upload_email':
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
        return render_template(email_template,
                               data=data,
                               page=page)


def send_extension_email(request_id, new_due_date, reason, email_content):
    """
    Function that sends email detailing a extension has been added to a request.

    :param request_id: FOIL request ID
    :param new_due_date: extended due date of the request
    :param reason: reason for extending the request
    :param email_content: content body of the email notification being sent

    :return: An email is sent to the requester and all agency users are bcc detailing an extension has been added to a
    request.
    """
    subject = 'Response Added'
    bcc = get_agencies_emails(request_id)
    requester_email = UserRequests.query.filter_by(request_id=request_id,
                                                   request_user_type=REQUESTER).first().user.email
    # Send email with files to requester and bcc agency_ein users as privacy option is release
    to = [requester_email]
    safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              "email_templates/email_extension",
                              to=to,
                              bcc=bcc,
                              agency_name="Department of Records and Information Services",
                              new_due_date=new_due_date.strftime('%A, %b %d, %Y'),
                              reason=reason,
                              )


def safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              template,
                              to=None,
                              bcc=None,
                              **kwargs):
    """
    Sends email and creates and stores the email object into the Emails table.

    :param request_id: FOIL request ID
    :param email_content: body of the email
    :param subject: subject of the email (current is for TESTING purposes)
    :param template: html template of the email body being rendered
    :param to: list of person(s) email is being sent to
    :param bcc: list of person(s) email is being bcc'ed

    :return: Sends email based on given arguments and creates and stores email object into the Emails table.
             Will print error if there is an error.
    """
    try:
        send_email(subject, template, to=to, bcc=bcc, **kwargs)
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
                      privacy='private'):
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

    # create event object
    event = Events(request_id=request_id,
                   user_id=user_guid,
                   auth_user_type=auth_user_type,
                   type=events_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id,
                   previous_response_value=previous_response_value,
                   new_response_value=new_response_value)
    # store event object
    create_object(obj=event)
