"""
.. module:: response.views.

   :synopsis: Handles the response URL endpoints for the OpenRecords application
"""
import os

import io

import app.lib.file_utils as fu

from datetime import datetime

from flask import (
    flash,
    request as flask_request,
    url_for,
    redirect,
    jsonify,
    current_app,
    after_this_request,
    abort,
    send_file
)
from flask_login import current_user, login_url

from app import login_manager, sentry
from app.constants import permission, request_date
from app.constants.pdf import EnvelopeDict
from app.constants.response_type import FILE, LETTER, EMAIL
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PRIVATE
from app.lib.utils import UserRequestException
from app.lib.date_utils import get_holidays_date_list
from app.lib.db_utils import delete_object
from app.lib.permission_utils import (
    has_permission,
    is_allowed
)
from app.lib.pdf import (
    generate_pdf_flask_response,
    generate_envelope_pdf,
    escape_latex_characters
)
from app.response import response
from app.models import (
    CommunicationMethods,
    Requests,
    Responses,
    ResponseTokens,
    UserRequests,
    Files,
    Notes,
    Instructions,
    Links,
    Letters,
    Envelopes
)
from app.response.utils import (
    add_note,
    add_file,
    add_link,
    add_extension,
    add_acknowledgment,
    add_denial,
    add_closing,
    add_quick_closing,
    add_reopening,
    add_response_letter,
    add_instruction,
    add_envelope,
    get_file_links,
    process_upload_data,
    send_file_email,
    process_email_template_request,
    process_letter_template_request,
    RespFileEditor,
    RespNoteEditor,
    RespInstructionsEditor,
    RespLinkEditor
)
from app.upload.utils import complete_upload


@response.route('/note/<request_id>', methods=['POST'])
@has_permission(permission.ADD_NOTE)
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

    current_request = Requests.query.filter_by(id=request_id).first()
    required_fields = []
    privacy = None
    is_editable = True
    is_requester = False

    if current_user.is_agency:
        required_fields.extend(['content',
                                'email-note-summary',
                                'privacy'])
    else:
        required_fields.append('content')
        is_editable = False
        privacy = RELEASE_AND_PRIVATE
        is_requester = True

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if not note_data.get(field, ''):
            flash('Uh Oh, it looks like the note {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_note(current_request.id,
             note_data['content'],
             note_data.get('email-note-summary'),
             note_data.get('privacy') or privacy,
             is_editable,
             is_requester)
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/file/<request_id>', methods=['POST'])
@has_permission(permission.ADD_FILE)
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
    release_public_links = []
    release_private_links = []
    private_links = []
    for file_data in files:
        quarantine_path = os.path.join(
            current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
            request_id,
            file_data)
        complete_upload.delay(current_request.id, quarantine_path, file_data)
        response_obj = add_file(current_request.id,
                                file_data,
                                files[file_data]['title'],
                                files[file_data]['privacy'],
                                is_editable=True)
        if not isinstance(response_obj, Files):
            flash(message=response_obj, category='danger')
        else:
            get_file_links(response_obj, release_public_links, release_private_links, private_links)
    send_file_email(request_id,
                    release_public_links,
                    release_private_links,
                    private_links,
                    flask_request.form['email-file-summary'],
                    flask_request.form['replace-string'],
                    flask_request.form['tz_name'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/acknowledgment/<request_id>', methods=['POST'])
@has_permission(permission.ACKNOWLEDGE)
def response_acknowledgment(request_id):
    required_fields = ['method', 'summary']
    if flask_request.form.get('method') == LETTER:
        if flask_request.form.get('letter-days', '-1') == '-1':
            required_fields.append('letter-date')
        else:
            required_fields.append('letter-days')

    if flask_request.form.get('method') == EMAIL:
        if flask_request.form.get('email-days', '-1') == '-1':
            required_fields.append('email-date')
            required_fields.append('info')
        else:
            required_fields.append('email-days')
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the acknowledgment {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    if flask_request.form.get('method') == LETTER:
        add_acknowledgment(request_id,
                           flask_request.form['info'].strip() or None,
                           flask_request.form['letter-days'],
                           flask_request.form['letter-date'],
                           flask_request.form['tz-name'] if flask_request.form['tz-name'] else current_app.config[
                               'APP_TIMEZONE'],
                           flask_request.form['summary'],
                           flask_request.form['method'],
                           flask_request.form.get('letter_templates'))
    else:
        add_acknowledgment(request_id,
                           flask_request.form['info'].strip() or None,
                           flask_request.form['email-days'],
                           flask_request.form['email-date'],
                           flask_request.form['tz-name'] if flask_request.form['tz-name'] else current_app.config[
                               'APP_TIMEZONE'],
                           flask_request.form['summary'],
                           flask_request.form['method'],
                           flask_request.form.get('letter_templates'))

    return redirect(url_for('request.view', request_id=request_id))


@response.route('/denial/<request_id>', methods=['POST'])
@has_permission(permission.DENY)
def response_denial(request_id):
    if flask_request.form.get('method') == EMAIL:
        required_fields = ['reasons',
                           'method',
                           'summary']
    else:
        required_fields = ['letter_templates',
                           'method',
                           'summary']
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the denial {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    add_denial(request_id,
               flask_request.form.getlist('reasons'),
               flask_request.form['summary'],
               flask_request.form['method'],
               flask_request.form.get('letter_templates'))
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/closing/<request_id>', methods=['POST'])
@has_permission(permission.CLOSE)
def response_closing(request_id):
    """
    Endpoint for closing a request that takes in form data from the front end.
    Required form data include:
        -reasons: a list of closing reasons
        -email-summary: string email body from the confirmation page

    :param request_id: FOIL request ID

    :return: redirect to view request page
    """
    if flask_request.form.get('method') == EMAIL:
        required_fields = ['reasons',
                           'method',
                           'summary']
    else:
        required_fields = ['letter_templates',
                           'method',
                           'summary']
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the closing {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    try:
        add_closing(request_id,
                    flask_request.form.getlist('reasons'),
                    flask_request.form['summary'],
                    flask_request.form['method'],
                    flask_request.form.get('letter_templates'))
    except UserRequestException as e:
        sentry.captureException()
        flash(str(e), category='danger')
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/quick-closing/<request_id>', methods=['POST'])
@has_permission(permission.ACKNOWLEDGE)
@has_permission(permission.CLOSE)
def response_quick_closing(request_id):
    """Endpoint for quick closing a request that takes in form data from the front end.

    Required form data include:
        email-date: the number of days the acknowledgement will take. Defaults to 20 for quick closings
        summary: string email body from the confirmation page

    Args:
        request_id: FOIL request ID

    Returns:
        Redirect to view request page
    """
    required_fields = ['email-date',
                       'summary']
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the acknowledgement/closing {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    try:
        add_quick_closing(request_id=request_id,
                          days=request_date.DEFAULT_QUICK_CLOSING_DAYS,
                          date=flask_request.form['email-date'],
                          tz_name=flask_request.form['tz-name'] if flask_request.form['tz-name'] else
                          current_app.config['APP_TIMEZONE'],
                          content=flask_request.form['summary'])
    except UserRequestException as e:
        sentry.captureException()
        flash(str(e), category='danger')
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/reopening/<request_id>', methods=['POST'])
@has_permission(permission.RE_OPEN)
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
    required_fields = ['date', 'tz-name', 'summary', 'method']

    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash('Uh Oh, it looks like the re-opening {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    if flask_request.form.get('method') == LETTER:
        if not flask_request.form.get('letter-template-id', ''):
            flash('Uh Oh, it looks like the re-opening letter-template-id is missing! '
                  'This is probably NOT your fault.', category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    if flask_request.form.get('method') == EMAIL:
        if not flask_request.form.get('reason-id', ''):
            flash('Uh Oh, it looks like the re-opening reason-id is missing! '
                  'This is probably NOT your fault.', category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_reopening(request_id,
                  flask_request.form['date'],
                  flask_request.form['tz-name'] if flask_request.form['tz-name'] else current_app.config[
                      'APP_TIMEZONE'],
                  flask_request.form['summary'],
                  flask_request.form.get('reason-id', None),
                  flask_request.form['method'],
                  flask_request.form.get('letter-template-id', None))
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/extension/<request_id>', methods=['POST'])
@has_permission(permission.EXTEND)
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
    if extension_data.get('method') == EMAIL:
        required_fields = ['length',
                           'reason',
                           'due-date',
                           'summary',
                           'method']
    else:
        required_fields = ['letter_templates',
                           'length',
                           'due-date-letter',
                           'summary',
                           'method']

    # TODO: Get copy from business, insert sentry issue key in message
    # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
    for field in required_fields:
        if not extension_data.get(field, ''):
            flash('Uh Oh, it looks like the extension {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    due_date = extension_data['due-date'] if extension_data['method'] == EMAIL else extension_data['due-date-letter']

    add_extension(request_id,
                  extension_data['length'],
                  extension_data['reason'],
                  due_date,
                  extension_data['tz-name'] if extension_data['tz-name'] else current_app.config['APP_TIMEZONE'],
                  extension_data['summary'],
                  extension_data['method'],
                  extension_data.get('letter_templates'))
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/link/<request_id>', methods=['POST'])
@has_permission(permission.ADD_LINK)
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
        if not link_data.get(field, ''):
            flash('Uh Oh, it looks like the link {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    add_link(request_id,
             link_data['title'],
             link_data['url'],
             link_data['email-link-summary'],
             link_data['privacy'],
             is_editable=True)
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/instruction/<request_id>', methods=['POST'])
@has_permission(permission.ADD_OFFLINE_INSTRUCTIONS)
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
        if not instruction_data.get(field, ''):
            flash('Uh Oh, it looks like the instruction {} is missing! '
                  'This is probably NOT your fault.'.format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))

    current_request = Requests.query.filter_by(id=request_id).first()
    add_instruction(current_request.id,
                    instruction_data['content'],
                    instruction_data['email-instruction-summary'],
                    instruction_data['privacy'],
                    is_editable=True)
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/envelope', methods=['POST'])
def response_generate_envelope():
    """
    Create an Envelope for the Request.
    :return: redirect to view request page
    """
    envelope_data = EnvelopeDict()
    request_id = flask_request.form.get('request_id')
    template = flask_request.form.get('template')
    envelope_data['request_id'] = request_id
    envelope_data['recipient_name'] = escape_latex_characters(str(flask_request.form.get('recipient_name')).upper())
    envelope_data['organization'] = escape_latex_characters(str(flask_request.form.get('organization')).upper())
    envelope_data['organization'] = " ".join(
        ['\\seqsplit{{{}}}'.format(i) for i in envelope_data['organization'].split()])
    envelope_data['street_address'] = '{} {}'.format(
        escape_latex_characters(str(flask_request.form.get('address_one')).upper()),
        escape_latex_characters(str(flask_request.form.get('address_two')).upper()))
    envelope_data['city'] = escape_latex_characters(str(flask_request.form.get('city')).upper())
    envelope_data['state'] = escape_latex_characters(str(flask_request.form.get('state')).upper())
    envelope_data['zipcode'] = escape_latex_characters(str(flask_request.form.get('zipcode')).upper())

    add_envelope(request_id, template, envelope_data)

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

    if current_user.is_anonymous or not resp.is_editable:
        return abort(403)

    patch_form = dict(flask_request.form)

    privacy = patch_form.pop('privacy', None)

    if privacy:
        # Check permissions for editing the privacy if required.

        permission_for_edit_type_privacy = {
            Files: permission.EDIT_FILE_PRIVACY,
            Notes: permission.EDIT_NOTE_PRIVACY,
            Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY,
            Links: permission.EDIT_LINK_PRIVACY
        }

        if not is_allowed(current_user, resp.request_id, permission_for_edit_type_privacy[type(resp)]):
            return abort(403)

    delete = patch_form.pop('deleted', None)

    if delete:
        confirmation = patch_form.pop('confirmation', None)
        if not confirmation:
            return abort(403)

        permission_for_delete_type = {
            Files: permission.DELETE_FILE,
            Notes: permission.DELETE_NOTE,
            Instructions: permission.DELETE_OFFLINE_INSTRUCTIONS,
            Links: permission.DELETE_LINK
        }

        if not is_allowed(current_user, resp.request_id, permission_for_delete_type[type(resp)]):
            return abort(403)

    if patch_form:
        # Mapping of Response types to permission values
        permission_for_type = {
            Files: permission.EDIT_FILE,
            Notes: permission.EDIT_NOTE,
            Instructions: permission.EDIT_OFFLINE_INSTRUCTIONS,
            Links: permission.EDIT_LINK
        }

        # If the current user does not have the permission to edit the response type, return 403
        if not is_allowed(current_user, resp.request_id, permission_for_type[type(resp)]):
            return abort(403)

    editor_for_type = {
        Files: RespFileEditor,
        Notes: RespNoteEditor,
        Instructions: RespInstructionsEditor,
        Links: RespLinkEditor,
    }
    editor = editor_for_type[type(resp)](current_user, resp, flask_request)

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
    if year:
        return jsonify(holidays=sorted(get_holidays_date_list(year)))
    else:
        return jsonify(holidays=sorted(get_holidays_date_list(int(datetime.now().year))))


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
    response_ = Responses.query.filter_by(id=response_id, deleted=False).one()

    if response_ is not None and response_.type == FILE:
        upload_path = os.path.join(
            current_app.config["UPLOAD_DIRECTORY"],
            response_.request_id
        )
        filepath_parts = (
            upload_path,
            response_.name
        )
        filepath = os.path.join(*filepath_parts)
        serving_path = os.path.join(
            current_app.config['UPLOAD_SERVING_DIRECTORY'],
            response_.request_id,
            response_.name
        )
        token = flask_request.args.get('token')
        if current_app.config['USE_VOLUME_STORAGE'] and not fu.exists(filepath):
            return abort(403)

        if response_.is_public:
            # then we just serve the file, anyone can view it
            @after_this_request
            def remove(resp):
                if current_app.config['USE_VOLUME_STORAGE']:
                    os.remove(serving_path)
                return resp

            return fu.send_file(*filepath_parts, as_attachment=True)
        else:
            # check presence of token in url
            if token is not None:
                resptok = ResponseTokens.query.filter_by(
                    token=token, response_id=response_id).first()
                if resptok is not None:
                    if response_.privacy != PRIVATE:
                        @after_this_request
                        def remove(resp):
                            if current_app.config['USE_VOLUME_STORAGE']:
                                os.remove(serving_path)
                            return resp

                        return fu.send_file(*filepath_parts, as_attachment=True)
                    else:
                        delete_object(resptok)

            # if token not included, nonexistent, or is expired, but user is logged in
            if current_user.is_authenticated:
                # user is agency or is public and response is not private
                if (((current_user.is_public and response_.privacy != PRIVATE)
                     or current_user.is_agency)
                        # user is associated with request
                        and UserRequests.query.filter_by(
                            request_id=response_.request_id,
                            user_guid=current_user.guid
                        ).first() is not None):
                    @after_this_request
                    def remove(resp):
                        if current_app.config['USE_VOLUME_STORAGE']:
                            os.remove(serving_path)
                        return resp

                    return fu.send_file(*filepath_parts, as_attachment=True)
                # user does not have permission to view file
                return abort(403)
            else:
                # redirect to login
                return redirect(login_url(
                    login_manager.login_view,
                    next_url=url_for('request.view', request_id=response_.request_id)
                ))
    return abort(404)  # file does not exist


@response.route('/letter', methods=['POST'])
def response_generate_letter():
    """
    Return letter template for the generate letter workflow step.

    Request Parameters:
    - request_id: FOIL request ID
    - agency_ein: Agency ID (for the specified request)
    - letter_template_id: Letter Template unique identifier

    Ex:
    {
        "request_id": "FOIL-XXX",
        "letter_template_id": 10
    }

    :return: the json response and HTTP status code
    Ex1:
    {
        "template": HTML rendered letter template,
        "header": "The following letter will be generated as a PDF:"
    }
    """
    data = flask_request.form
    request_id = data['request_id']

    return process_letter_template_request(request_id, data)


@response.route('/envelope/<request_id>/<response_id>')
def response_get_envelope(request_id, response_id):
    """
    Return a PDF envelope as an attachment.

    :param request_id: FOIL Request ID for which the letter exists
    :param response_id: Response ID for the letter.
    :return: PDF Attachment.
    """

    if current_user.is_authenticated and current_user.is_agency:
        request = Requests.query.filter_by(id=request_id).one()

        if current_user not in request.agency_users:
            return jsonify({'error': 'unauthorized'}), 403
        envelope = Envelopes.query.filter_by(id=response_id).one()

        f = generate_envelope_pdf(envelope.latex)

        return send_file(
            io.BytesIO(f),
            mimetype='application/pdf',
            as_attachment=True,
            attachment_filename=
            '{request_id}_envelope.pdf'.format(request_id=request_id)
        )


@response.route('/letter/<request_id>', methods=['POST'])
@has_permission(permission.GENERATE_LETTER)
def response_letter(request_id):
    """

    :param request_id:
    :return:
    """
    required_fields = ['letter-summary',
                       'letter_templates']
    for field in required_fields:
        if not flask_request.form.get(field, ''):
            flash("Uh Oh, it looks like the {} is missing! "
                  "This is probably NOT your fault.".format(field), category='danger')
            return redirect(url_for('request.view', request_id=request_id))
    add_response_letter(request_id, flask_request.form['letter-summary'], flask_request.form['letter_templates'])
    return redirect(url_for('request.view', request_id=request_id))


@response.route('/letter/<request_id>/<response_id>')
def response_get_letter(request_id, response_id):
    """
    Return a PDF letter as an attachment.

    :param request_id: FOIL Request ID for which the letter exists
    :param response_id: Response ID for the letter.
    :return: PDF Attachment.
    """
    if current_user.is_authenticated and current_user.is_agency:
        request = Requests.query.filter_by(id=request_id).one()
        if current_user not in request.agency_users:
            return jsonify({'error': 'unauthorized'}), 403
        response_ = Responses.query.filter_by(id=response_id).one()
        if response_.type == LETTER:
            letter = Letters.query.filter_by(id=response_id).one()
        else:
            cm = CommunicationMethods.query.filter_by(response_id=response_id, method_type=LETTER).one()
            letter = Letters.query.filter_by(id=cm.method_id).one()

        return generate_pdf_flask_response(letter.content)
    return jsonify({'error': 'unauthorized'}), 403
