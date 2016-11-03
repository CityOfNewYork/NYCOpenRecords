"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""

import json

from flask import (
    flash,
    request as flask_request,
    url_for,
    redirect,
    jsonify,
)
from flask_login import current_user

from app.constants.response_privacy import PRIVATE
from app.models import Requests, Responses
from app.response import response
from app.constants import response_type
from app.response.utils import (
    add_note,
    add_file,
    add_link,
    add_extension,
    add_instruction,
    process_upload_data,
    send_file_email,
    process_privacy_options,
    process_email_template_request,
    RespFileEditor
)
from urllib.request import urlopen


@response.route('/note/<request_id>', methods=['POST'])
def response_note(request_id):
    """
    Note response endpoint that takes in the content of a note for a specific request from the frontend.
    Check if required data from form is retrieved.
    Flash error message if required form data is missing.
    Call add_link to process the extension form data.

    :param request_id: FOIL request ID for the specific note.
    :return: redirect to view request page
    """
    note_data = flask_request.form

    required_fields = ['content',
                       'email-note-summary',
                       'privacy']

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if note_data.get(field) is None:
            flash('Uh Oh, it looks like the instruction {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    current_request = Requests.query.filter_by(id=request_id).first()
    add_note(current_request.id,
             note_data['content'],
             note_data['email-note-summary'],
             note_data['privacy'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/file/<request_id>', methods=['POST'])
def response_file(request_id):
    """
    File response endpoint that takes in the metadata of a file for a specific request from the frontend.
    Call process_upload_data to process the uploaded file form data.
    Pass data into helper function in response.utils to update changes into database.
    Send email notification to requester and bcc agency users if privacy is release.
    Render specific tempalte and send email notification bcc agency users if privacy is private.

    :param request_id: FOIL request ID for the specific file.
    :return: redirect to view request page
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    files = process_upload_data(flask_request.form)
    for file_data in files:
        add_file(current_request.id,
                 file_data,
                 files[file_data]['title'],
                 files[file_data]['privacy'])
    file_options = process_privacy_options(files)
    email_content = flask_request.form['email-file-summary']
    for privacy, files in file_options.items():
        if privacy == PRIVATE:
            send_file_email(request_id,
                            privacy,
                            files,
                            None,
                            email_template='email_templates/email_private_file_upload.html')
        else:
            send_file_email(request_id,
                            privacy,
                            files,
                            email_content)
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/extension/<request_id>', methods=['POST'])
def response_extension(request_id):
    """
    Extension response endpoint that takes in the metadata of an extension for a specific request from the frontend.
    Check if required data from form is retrieved.
    Flash error message if required form data is missing.
    Call add_extension to process the extension form data.

    :param request_id: FOIL request ID for the specific extension.

    :return: redirect to view request page
    """
    extension_data = flask_request.form

    required_fields = ['length',
                       'reason',
                       'due-date',
                       'email-extension-summary']

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if extension_data.get(field) is None:
            flash('Uh Oh, it looks like the extension {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_extension(request_id,
                  extension_data['length'],
                  extension_data['reason'],
                  extension_data['due-date'],
                  extension_data['email-extension-summary'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/link/<request_id>', methods=['POST'])
def response_link(request_id):
    """
    Link response endpoint that takes in the metadata of a link for a specific request from the frontend.
    Check if required data from form is retrieved.
    Flash error message if required form data is missing.
    Call add_link to process the extension form data.

    :param request_id: FOIL request ID for the specific link.

    :return: redirect to view request page
    """
    link_data = flask_request.form

    required_fields = ['title',
                       'url',
                       'email-link-summary',
                       'privacy']

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if link_data.get(field) is None:
            flash('Uh Oh, it looks like the link {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_link(request_id,
             link_data['title'],
             link_data['url'],
             link_data['email-link-summary'],
             link_data['privacy'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/instruction/<request_id>', methods=['POST'])
def response_instructions(request_id):
    """
    Instruction response endpoint that takes in from the frontend, the content of a instruction for a specific request.
    Check if required data from form is retrieved.
    Flash error message if required form data is missing.
    Call add_instruction to process the extension form data.

    :param request_id: FOIL request ID for the specific note.

    :return: redirect to view request page
    """
    instruction_data = flask_request.form

    required_fields = ['content',
                       'email-instruction-summary',
                       'privacy']

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if instruction_data.get(field) is None:
            flash('Uh Oh, it looks like the instruction {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    current_request = Requests.query.filter_by(id=request_id).first()
    add_instruction(current_request.id,
                    instruction_data['content'],
                    instruction_data['email-instruction-summary'],
                    instruction_data['privacy'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/email', methods=['POST'])
def response_email():
    """
    Return email template for a particular response workflow step.

    Request Parameters:
    - request_id: FOIL request ID
    - type: response type
    - privacy: selected privacy option
    - extension: data for populating html template
        - length: selected value of extension length (-1, 20, 30, 60, 90)
        - custom_due_date: new custom due date of request (default is current request due_date)
        - reason: reason for extension
    - link: data for populating html template
        - url: url link inputted by user from front end
    - offline_instructions: data for populating html template
        - instruction: json object with key and values of content and privacy
    - note: data for populating html template
        - note: json object with key and values of content and privacy
    - file: data for populating html template
        - files: json object with key and values of filename and privacy
    - email_content: (on second next click) html template of specific response which may include edits

    Ex:
    {
         "request_id": "FOIL-XXX",
         "type": "extension",
         "extension": {
               "length": "20",
               "custom_due_date": "2016-11-14",
               "reason": "We need more time to process your request."
         }
         "email_content": HTML
    }

    :return: the HTML of the rendered template
    """
    data = flask_request.form
    request_id = data['request_id']
    email_template = process_email_template_request(request_id, data)
    return email_template


@response.route('/url_checker', methods=['GET'])
def check_url():
    """
    Check the incoming url link's HTTP code status.

    :return: If url link is valid, string 'Valid URL' and 200 status code is returned
             If url link is invalid, string 'Invalid URL' and 400 status code is returned
    """
    url_link = flask_request.args['url']
    try:
        url_status = urlopen(url_link).getcode()
    except ValueError as e:
        print(e)
        return 'Invalid URL', 400

    if url_status == 200:
        return 'Valid URL', 200
    else:
        return 'Invalid URL', 400


# TODO: Implement response route for sms
@response.route('/sms/<request_id>', methods=['GET', 'POST'])
def response_sms():
    pass


# TODO: Implement response route for push
@response.route('/push/<request_id>', methods=['GET', 'POST'])
def response_push():
    pass


# TODO: Implement response route for visiblity
@response.route('/visiblity/<request_id>', methods=['GET', 'POST'])
def response_visiblity():
    pass


@response.route('/<response_id>', methods=['PUT'])
def edit_response(response_id):
    """
    Edit a response's privacy and its metadata.

    Expects a request body containing field names and updated values.
    Ex:
    {
        'privacy': 'release_public',
        'title': 'new title'
        'filename': 'uploaded_file_name.ext'  # REQUIRED for updates to Files metadata
    }
    Response body consists of both the old and updated data, or an error message.
    """
    if current_user.is_anonymous:
        return {}, 403
    # TODO: user permissions check
    resp = Responses.query.filter_by(id=response_id).first()
    editor_for_type = {
        response_type.FILE: RespFileEditor,
        # response_type.NOTE: RespNoteEditor,
        # ...
    }
    editor = editor_for_type[resp.type](current_user, resp, flask_request)
    if editor.errors:
        http_response = {"errors": editor.errors}
    else:
        http_response = {
            "old": editor.data_old,
            "new": editor.data_new
        }
    return jsonify(http_response), 200
