"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""
import os

import app.lib.file_utils as fu

from datetime import datetime

from flask import (
    flash,
    request as flask_request,
    url_for,
    redirect,
    jsonify,
    current_app,
)
from flask_login import current_user

from app.constants.response_type import FILE
from app.lib.date_utils import get_holidays_date_list
from app.lib.db_utils import delete_object
from app.response import response
from app.models import (
    Requests,
    Responses,
    ResponseTokens,
    UserRequests,
    Files,
    Notes,
    Instructions,
    Links
)
from app.response.utils import (
    add_note,
    add_file,
    add_link,
    add_extension,
    add_acknowledgment,
    add_denial,
    add_closing,
    add_reopening,
    add_instruction,
    get_file_links,
    process_upload_data,
    send_file_email,
    process_email_template_request,
    RespFileEditor,
    RespNoteEditor,
    RespInstructionsEditor,
    RespLinkEditor
)


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
    Render specific template and send email notification bcc agency users if privacy is private.

    :param request_id: FOIL request ID for the specific file.

    :return: redirect to view request page
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    files = process_upload_data(flask_request.form)
    agency_file_links = {
        'private': {},
        'release': {}
    }
    requester_file_links = dict()
    for file_data in files:
        response_obj = add_file(current_request.id,
                                file_data,
                                files[file_data]['title'],
                                files[file_data]['privacy'])
        get_file_links(response_obj, agency_file_links, requester_file_links)
    email_content = flask_request.form['email-file-content']
    send_file_email(request_id, agency_file_links, requester_file_links, email_content)
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/acknowledgment/<request_id>', methods=['POST'])
def response_acknowledgment(request_id):
    required_fields = ['date',
                       'days',
                       'email-summary']
    if flask_request.form.get('days', '-1') == '-1':
        required_fields.append('info')
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the acknowledgment {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_acknowledgment(request_id,
                       flask_request.form['info'].strip() or None,
                       flask_request.form['days'],
                       flask_request.form['date'],
                       flask_request.form['tz-name'],
                       flask_request.form['email-summary'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/denial/<request_id>', methods=['POST'])
def response_denial(request_id):
    required_fields = ['reasons', 'email-summary']

    for field in required_fields:
        if flask_request.form.get(field) is None:
            flash('Uh Oh, it looks like the denial {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_denial(request_id,
               flask_request.form.getlist('reasons'),
               flask_request.form['email-summary'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/closing/<request_id>', methods=['POST'])
def response_closing(request_id):
    """
    Endpoint for closing a request that takes in form data from the front end.
    Required form data include:
        -reasons: a list of closing reasons
        -email-summary: string email body from the confirmation page

    :param request_id: FOIL request ID

    :return: redirect to view request page
    """
    required_fields = ['reasons', 'email-summary']

    for field in required_fields:
        if flask_request.form.get(field) is None:
            flash('Uh Oh, it looks like the closing {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

        add_closing(request_id,
                    flask_request.form.getlist('reasons'),
                    flask_request.form['email-summary'])
        return redirect(url_for('request.view', request_id=request_id))


@response.route('/reopening/<request_id>', methods=['POST'])
def response_reopening(request_id):
    """
    Endpoint for reopening a request that takes in form data from the frontend.
    Required form data include:
        -date: string of new date of request completion
        -tz-name: name of the timezone the user is accessing the application in
        -email-summary: string email body from the confirmation page

    :param request_id: FOIL request ID

    :return: redirect to view request page
    """
    required_fields = ['date', 'tz-name', 'email-summary']

    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the acknowledgement {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_reopening(request_id,
                  flask_request.form['date'],
                  flask_request.form['tz-name'],
                  flask_request.form['email-summary'])
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
                  extension_data['tz-name'],
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

    :return: the json response and HTTP status code
    Ex1:
    {
        "template": HTML rendered response template,
        "header": "The following will be emailed to all associated participants:"
    }

    Ex2:
    {
        "error": "No changes detected."
    }
    """
    data = flask_request.form
    request_id = data['request_id']
    return process_email_template_request(request_id, data)


# TODO: Implement response route for sms
@response.route('/sms/<request_id>', methods=['GET', 'POST'])
def response_sms(request_id):
    pass


# TODO: Implement response route for push
@response.route('/push/<request_id>', methods=['GET', 'POST'])
def response_push(request_id):
    pass


# TODO: Implement response route for visiblity
@response.route('/visiblity/<request_id>', methods=['GET', 'POST'])
def response_visiblity(request_id):
    pass


@response.route('/<response_id>', methods=['PATCH'])
def patch(response_id):
    """
    Edit a response's fields and send a notification email.

    Expects a request body containing field names and updated values.
    Ex:
    {
        'privacy': 'release_public',
        'title': 'new title'
        'filename': 'uploaded_file_name.ext'  # REQUIRED for updates to Files metadata
    }
    Ex (for delete):
    {
        'deleted': true,
        'confirmation': string checked against 'DELETE'
            if the strings do not match, the 'deleted' field will not be updated
    }

    :return: on success:
    {
        'old': { original attributes and their values }
        'new': { updated attributes and their values }
    }

    """
    resp = Responses.query.filter_by(id=response_id, deleted=False).one()

    user = resp.request.requester \
        if current_user.is_anonymous else current_user
    # FIXME: this is only for testing purposes, anonymous users cannot do anything with responses

    editor_for_type = {
        Files: RespFileEditor,
        Notes: RespNoteEditor,
        Instructions: RespInstructionsEditor,
        Links: RespLinkEditor,
        # ...
    }
    editor = editor_for_type[type(resp)](user, resp, flask_request)
    if editor.errors:
        http_response = {"errors": editor.errors}
    else:
        if editor.no_change:  # TODO: unittest
            http_response = {
                "message": "No changes detected."
            }
        else:
            http_response = {
                "old": editor.data_old,
                "new": editor.data_new
            }
    return jsonify(http_response), 200


@response.route('/get_yearly_holidays/<int:year>', methods=['GET'])
def get_yearly_holidays(year):
    """
    Retrieve a list of dates that are holidays in the specified year

    :param year: 4-digit year.

    :return: List of strings ["YYYY-MM-DD"]
    """
    return jsonify(holidays=sorted(get_holidays_date_list(year)))


@response.route('/<response_id>', methods=["GET"])
def get_response_content(response_id):
    """
    Currently only supports File Responses.

    Request Parameters:
    - token: (optional) ephemeral access token

    :return: response file contents or
             redirect to login if user not authenticated and no token provided or
             400 error if response/file not found
    """
    # TODO: response_; check if private first, send to "this file is private" page
    response = Responses.query.filter_by(id=response_id, deleted=False).one()
    if response is not None and response.type == FILE:
        upload_path = os.path.join(
            current_app.config["UPLOAD_DIRECTORY"],
            response.request_id
        )
        filepath_parts = (
            upload_path,
            response.name
        )
        filepath = os.path.join(*filepath_parts)
        token = flask_request.args.get('token')
        if token is not None:
            resptok = ResponseTokens.query.filter_by(
                token=token, response_id=response_id).first()
            if resptok is not None:
                if (datetime.utcnow() < resptok.expiration_date
                   and fu.exists(filepath)):
                    return fu.send_file(*filepath_parts, as_attachment=True)
                else:
                    delete_object(resptok)
        else:
            if current_user.is_authenticated:
                if ((current_user.is_public or current_user.is_agency)
                   and UserRequests.query.filter_by(
                        request_id=response.request_id,
                        user_guid=current_user.guid,
                        auth_user_type=current_user.auth_user_type).first() is not None
                   and fu.exists(filepath)):
                    return fu.send_file(*filepath_parts, as_attachment=True)
            else:
                return redirect(url_for(
                    'auth.index',
                    sso2=True,
                    return_to=flask_request.base_url))
    return '', 400  # TODO: error pages
