"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
import json
from datetime import datetime
from urllib.parse import urljoin, urlencode

import os
import re
from abc import ABCMeta, abstractmethod
from cached_property import cached_property
from flask import (
    current_app,
    request as flask_request,
    render_template,
    render_template_string,
    url_for,
    jsonify,
    Markup
)
from flask_login import current_user
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

import app.lib.file_utils as fu
from app import email_redis, calendar, sentry
from app.auth.utils import find_user_by_email
from app.constants import (
    event_type,
    response_type,
    response_privacy,
    request_status,
    determination_type,
    UPDATED_FILE_DIRNAME,
    DELETED_FILE_DIRNAME,
    DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS,
    EMAIL_TEMPLATE_FOR_TYPE,
    CONFIRMATION_EMAIL_HEADER_TO_REQUESTER,
    CONFIRMATION_EMAIL_HEADER_TO_AGENCY,
    CONFIRMATION_LETTER_HEADER_TO_REQUESTER,
    EMAIL_TEMPLATE_FOR_EVENT
)
from app.constants import (
    permission,
    TINYMCE_EDITABLE_P_TAG
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PUBLIC, RELEASE_AND_PRIVATE
from app.lib.date_utils import (
    get_next_business_day,
    get_due_date,
    process_due_date,
    get_release_date,
    local_to_utc,
    utc_to_local,
)
from app.lib.db_utils import create_object, update_object, delete_object
from app.lib.email_utils import send_email, get_assigned_users_emails
from app.lib.pdf import (
    generate_pdf,
    generate_envelope,
    generate_envelope_pdf
)
from app.lib.redis_utils import redis_get_file_metadata, redis_delete_file_metadata
from app.lib.utils import eval_request_bool, UserRequestException, DuplicateFileException
from app.models import (
    CommunicationMethods,
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
    LetterTemplates,
    Letters,
    Envelopes,
    EnvelopeTemplates
)
from app.request.api.utils import create_request_info_event
from app.upload.utils import complete_upload

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
        sentry.captureException()

    try:
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
    except DuplicateFileException as e:
        sentry.captureException()
        return str(e)


def add_note(request_id, note_content, email_content, privacy, is_editable, is_requester):
    """
    Create and store the note object for the specified request.
    Store the note content into the Notes table.
    Provides parameters for the process_response function to create and store responses and events object.

    :param request_id: FOIL request ID for the note
    :param note_content: string content of the note to be created and stored as a note object
    :param email_content: email body content of the email to be created and stored as a email object
    :param privacy: The privacy option of the note
    :param is_editable: editability of the note
    :param is_requester: requester is creator of the note

    """
    response = Notes(request_id, privacy, note_content, is_editable=is_editable)
    create_object(response)
    create_response_event(event_type.NOTE_ADDED, response)
    subject = 'Note Added to {}'.format(request_id)
    if is_requester:
        email_content = render_template('email_templates/email_response_note.html',
                                        from_requester=is_requester,
                                        agency_name=response.request.agency.name,
                                        note_content=note_content,
                                        page=urljoin(flask_request.host_url,
                                                     url_for('request.view', request_id=request_id)),
                                        request_id=request_id
                                        )
        subject = 'Note Added to {}'.format(request_id)
    else:
        if privacy != PRIVATE:
            subject = 'Response Added to {} - Note'.format(request_id)
    _send_response_email(request_id,
                         privacy,
                         email_content,
                         subject)


def add_acknowledgment(request_id, info, days, date, tz_name, content, method, letter_template_id):
    """
    Create and store an acknowledgement-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param info: additional information pertaining to the acknowledgment
    :param days: days until request completion
    :param date: date of request completion
    :param tz_name: client's timezone name
    :param content: body text associated with the acknowledgment
    :param method: the communication method of the acknowledgement (response_type.LETTER or response_type.EMAIL)
    :param letter_template_id: id of the letter template

    """
    request = Requests.query.filter_by(id=request_id).one()

    if not request.was_acknowledged:
        previous_due_date = {"due_date": request.due_date.isoformat()}
        previous_status = request.status
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
        create_response_event(event_type.REQ_ACKNOWLEDGED, response, previous_value=previous_due_date)
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status},
            new_value={'status': request.status}
        )
        if method == response_type.LETTER:
            letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()
            letter_id = _add_letter(request_id, letter_template.title, content,
                                    event_type.ACKNOWLEDGMENT_LETTER_CREATED)
            _create_communication_method(response.id, letter_id, response_type.LETTER)
            letter = generate_pdf(content)
            email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                          EMAIL_TEMPLATE_FOR_EVENT[event_type.ACKNOWLEDGMENT_LETTER_CREATED])
            email_content = render_template(email_template,
                                            request_id=request_id,
                                            agency_name=request.agency.name,
                                            user=current_user
                                            )
            email_id = safely_send_and_add_email(request_id,
                                                 email_content,
                                                 'Request {} Acknowledged - Letter'.format(request_id),
                                                 to=get_assigned_users_emails(request_id),
                                                 attachment=letter,
                                                 filename=secure_filename(
                                                     '{}_acknowledgment_letter.pdf'.format(request_id)),
                                                 mimetype='application/pdf')
            _create_communication_method(response.id, email_id, response_type.EMAIL)
        else:
            email_id = _send_response_email(request_id,
                                            privacy,
                                            content,
                                            'Request {} Acknowledged'.format(request_id))
            _create_communication_method(response.id, email_id, response_type.EMAIL)


def add_denial(request_id, reason_ids, content, method, letter_template_id):
    """
    Create and store a denial-determination response for
    the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param reason_ids: reason for denial
    :param content: body text associated with the denial
    :param method: the communication method of the denial (response_type.LETTER or response_type.EMAIL)
    :param letter_template_id: id of the letter template

    """
    request = Requests.query.filter_by(id=request_id).one()
    if request.status != request_status.CLOSED:
        previous_status = request.status
        previous_date_closed = request.date_closed.isoformat() if request.date_closed else None
        update_vals = {'status': request_status.CLOSED}
        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            update_vals['date_closed'] = get_next_business_day()
        else:
            update_vals['date_closed'] = datetime.utcnow()
        if not request.privacy['agency_request_summary'] and request.agency_request_summary is not None:
            update_vals['agency_request_summary_release_date'] = calendar.addbusdays(datetime.utcnow(),
                                                                                     RELEASE_PUBLIC_DAYS)
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        else:
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status, 'date_closed': previous_date_closed},
            new_value={'status': request.status, 'date_closed': request.date_closed.isoformat()}
        )

        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            # push the denial date to the next business day if it is a weekend/holiday
            # or if it is before the date submitted
            response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.DENIAL,
                format_determination_reasons(reason_ids),
                date_modified=get_next_business_day()
            )
        else:
            response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.DENIAL,
                format_determination_reasons(reason_ids)
            )
        if method == response_type.LETTER:
            response.reason = 'A letter will be mailed to the requester.'
        create_object(response)
        create_response_event(event_type.REQ_DENIED, response)
        request.es_update()
        if method == response_type.LETTER:
            letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()
            letter_id = _add_letter(request_id, letter_template.title, content, event_type.DENIAL_LETTER_CREATED)
            _create_communication_method(response.id, letter_id, response_type.LETTER)
            letter = generate_pdf(content)
            email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                          EMAIL_TEMPLATE_FOR_EVENT[event_type.DENIAL_LETTER_CREATED])
            email_content = render_template(email_template,
                                            request_id=request_id,
                                            agency_name=request.agency.name,
                                            user=current_user
                                            )
            email_id = safely_send_and_add_email(request_id,
                                                 email_content,
                                                 'Request {} Closed'.format(request_id),
                                                 to=get_assigned_users_emails(request_id),
                                                 attachment=letter,
                                                 filename=secure_filename('{}_denial_letter.pdf'.format(request_id)),
                                                 mimetype='application/pdf')
            _create_communication_method(response.id, email_id, response_type.EMAIL)
        else:
            email_id = _send_response_email(request_id,
                                            RELEASE_AND_PUBLIC,
                                            content,
                                            'Request {} Closed'.format(request_id))

            _create_communication_method(response.id, email_id, response_type.EMAIL)
    else:
        raise UserRequestException(action="close",
                                   request_id=request_id,
                                   reason="Request is already closed")


def add_closing(request_id, reason_ids, content, method, letter_template_id):
    """
    Create and store a closing-determination response for the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param reason_ids: reason(s) for closing
    :param content: body text associated with the closing
    :param method: the communication method of the closing (response_type.LETTER or response_type.EMAIL)
    :param letter_template_id: id of the letter template

    """
    request = Requests.query.filter_by(id=request_id).one()
    if request.status != request_status.CLOSED and (
            request.was_acknowledged or request.was_reopened):
        previous_status = request.status
        previous_date_closed = request.date_closed.isoformat() if request.date_closed else None
        update_vals = {'status': request_status.CLOSED}
        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            update_vals['date_closed'] = get_next_business_day()
        else:
            update_vals['date_closed'] = datetime.utcnow()
        if not request.privacy['agency_request_summary'] and request.agency_request_summary is not None:
            update_vals['agency_request_summary_release_date'] = calendar.addbusdays(datetime.utcnow(),
                                                                                     RELEASE_PUBLIC_DAYS)
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        else:
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status, 'date_closed': previous_date_closed},
            new_value={'status': request.status, 'date_closed': request.date_closed.isoformat()}
        )

        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            # push the closing date to the next business day if it is a weekend/holiday
            # or if it is before the date submitted
            response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(reason_ids),
                date_modified=get_next_business_day()
            )
        else:
            response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(reason_ids)
            )
        if method == response_type.LETTER:
            response.reason = 'A letter will be mailed to the requester.'
        create_object(response)
        create_response_event(event_type.REQ_CLOSED, response)
        request.es_update()
        if method == response_type.LETTER:
            letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()
            letter_id = _add_letter(request_id, letter_template.title, content, event_type.CLOSING_LETTER_CREATED)
            _create_communication_method(response.id, letter_id, response_type.LETTER)
            letter = generate_pdf(content)
            email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                          EMAIL_TEMPLATE_FOR_EVENT[event_type.CLOSING_LETTER_CREATED])
            email_content = render_template(email_template,
                                            request_id=request_id,
                                            agency_name=request.agency.name,
                                            user=current_user
                                            )
            email_id = safely_send_and_add_email(request_id,
                                                 email_content,
                                                 'Request {} Closed'.format(request_id),
                                                 to=get_assigned_users_emails(request_id),
                                                 attachment=letter,
                                                 filename=secure_filename('{}_closing_letter.pdf'.format(request_id)),
                                                 mimetype='application/pdf')
            _create_communication_method(response.id, email_id, response_type.EMAIL)
        else:
            email_id = _send_response_email(request_id,
                                            RELEASE_AND_PUBLIC,
                                            content,
                                            'Request {} Closed'.format(request_id))

            _create_communication_method(response.id, email_id, response_type.EMAIL)
    else:
        raise UserRequestException(action="close",
                                   request_id=request_id,
                                   reason="Request is already closed or has not been acknowledged")


def add_quick_closing(request_id, days, date, tz_name, content):
    """Create and store an acknowledgement-determination response followed by a closing-determination response for
    the specified request and update the request accordingly.

    Args:
        request_id: FOIL request ID
        days: days until request completion
        date: date of request completion
        tz_name: client's timezone name
        content: body text associated with the acknowledgment/closing
    """
    # Acknowledgement actions
    request = Requests.query.filter_by(id=request_id).one()
    if not request.was_acknowledged:
        previous_due_date = {'due_date': request.due_date.isoformat()}
        previous_status = request.status
        new_due_date = _get_new_due_date(request_id, days, date, tz_name)
        update_object(
            {'due_date': new_due_date,
             'status': request_status.IN_PROGRESS},
            Requests,
            request_id
        )
        privacy = RELEASE_AND_PUBLIC
        acknowledgement_response = Determinations(
            request_id,
            privacy,
            determination_type.ACKNOWLEDGMENT,
            None,
            new_due_date,
        )
        create_object(acknowledgement_response)
        create_response_event(event_type.REQ_ACKNOWLEDGED, acknowledgement_response, previous_value=previous_due_date)
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status},
            new_value={'status': request.status}
        )
    else:
        raise UserRequestException(action='acknowledge',
                                   request_id=request_id,
                                   reason='Request has already been acknowledged')

    # Closing actions
    if request.status != request_status.CLOSED and (
            request.was_acknowledged or request.was_reopened):
        previous_status = request.status
        previous_date_closed = request.date_closed.isoformat() if request.date_closed else None
        update_vals = {'status': request_status.CLOSED}
        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            update_vals['date_closed'] = get_next_business_day()
        else:
            update_vals['date_closed'] = datetime.utcnow()
        if not request.privacy['agency_request_summary'] and request.agency_request_summary is not None:
            update_vals['agency_request_summary_release_date'] = calendar.addbusdays(datetime.utcnow(),
                                                                                     RELEASE_PUBLIC_DAYS)
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        else:
            update_object(
                update_vals,
                Requests,
                request_id,
                es_update=False
            )
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status, 'date_closed': previous_date_closed},
            new_value={'status': request.status, 'date_closed': request.date_closed.isoformat()}
        )
        reason = Reasons.query.filter_by(title='Fulfilled via Walk In').one()
        if not calendar.isbusday(datetime.utcnow()) or datetime.utcnow().date() < request.date_submitted.date():
            # push the closing date to the next business day if it is a weekend/holiday
            # or if it is before the date submitted
            closing_response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons([reason.id]),
                date_modified=get_next_business_day()
            )
        else:
            closing_response = Determinations(
                request_id,
                RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons([reason.id])
            )
        create_object(closing_response)
        create_response_event(event_type.REQ_CLOSED, closing_response)
        request.es_update()
    else:
        raise UserRequestException(action='close',
                                   request_id=request_id,
                                   reason='Request is already closed or has not been acknowledged')

    email_id = _send_response_email(request_id,
                                    privacy,
                                    content,
                                    'Request {} Acknowledged and Closed'.format(request_id))
    # Create 2 CommunicationMethod objects, one for each determination
    _create_communication_method(acknowledgement_response.id, email_id, response_type.EMAIL)
    _create_communication_method(closing_response.id, email_id, response_type.EMAIL)


def add_reopening(request_id, date, tz_name, content, reason, method, letter_template_id=None):
    """
    Create and store a re-opened-determination for the specified request and update the request accordingly.

    :param request_id: FOIL request ID
    :param date: string of new date of request completion
    :param tz_name: client's timezone name
    :param content: email body associated with the reopened request
    :param reason: Reason for re-opening
    :param method: Method of delivery (email or letters)
    :param letter_template_id: id of the letter template, if generating a letter

    """
    request = Requests.query.filter_by(id=request_id).one()
    if request.status == request_status.CLOSED:
        previous_status = request.status
        date = datetime.strptime(date, '%m/%d/%Y')
        previous_due_date = {"due_date": request.due_date.isoformat()}
        new_due_date = process_due_date(local_to_utc(date, tz_name))
        privacy = RELEASE_AND_PUBLIC
        reason = Reasons.query.filter_by(id=reason).one().content
        response = Determinations(
            request_id,
            privacy,
            determination_type.REOPENING,
            reason,
            new_due_date
        )
        create_object(response)
        create_response_event(event_type.REQ_REOPENED, response, previous_value=previous_due_date)
        update_object(
            {'status': request_status.IN_PROGRESS,
             'due_date': new_due_date,
             'agency_request_summary_release_date': None},
            Requests,
            request_id
        )
        create_request_info_event(
            request_id,
            type_=event_type.REQ_STATUS_CHANGED,
            previous_value={'status': previous_status},
            new_value={'status': request.status}
        )

        if method == response_type.EMAIL:
            email_id = _send_response_email(request_id,
                                            privacy,
                                            content,
                                            'Request {} Re-Opened'.format(request_id))
            _create_communication_method(response.id,
                                         email_id,
                                         response_type.EMAIL)

        elif method == response_type.LETTER:
            letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()

            letter_id = _add_letter(request_id, letter_template.title, content,
                                    event_type.REOPENING_LETTER_CREATED)

            _create_communication_method(response.id, letter_id, response_type.LETTER)

            letter = generate_pdf(content)

            email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                          EMAIL_TEMPLATE_FOR_EVENT[event_type.REOPENING_LETTER_CREATED])

            email_content = render_template(email_template,
                                            request_id=request_id,
                                            agency_name=request.agency.name,
                                            user=current_user
                                            )
            email_id = safely_send_and_add_email(request_id,
                                                 email_content,
                                                 'Request {} Reopened - Letter'.format(request_id),
                                                 to=get_assigned_users_emails(request_id),
                                                 attachment=letter,
                                                 filename=secure_filename(
                                                     '{}_reopening_letter.pdf'.format(request_id)),
                                                 mimetype='application/pdf')
            _create_communication_method(response.id, email_id, response_type.EMAIL)


def add_extension(request_id, length, reason, custom_due_date, tz_name, content, method, letter_template_id):
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
    :param content: body text associated with the extension
    :param method: the communication method of the extension (response_type.LETTER or response_type.EMAIL)
    :param letter_template_id: id of the letter template

    """
    request = Requests.query.filter_by(id=request_id).one()
    previous_due_date = {"due_date": request.due_date.isoformat()}
    new_due_date = _get_new_due_date(request_id, length, custom_due_date, tz_name)
    days_until_due = calendar.busdaycount(datetime.utcnow(), new_due_date.replace(hour=23, minute=59, second=59))
    if new_due_date < datetime.utcnow():
        new_status = request_status.OVERDUE
    elif days_until_due <= current_app.config['DUE_SOON_DAYS_THRESHOLD']:
        new_status = request_status.DUE_SOON
    else:
        new_status = request_status.IN_PROGRESS
    update_object(
        {
            'due_date': new_due_date,
            'status': new_status
        },
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
    if method == response_type.LETTER:
        response.reason = 'A letter will be mailed to the requester.'
    create_object(response)
    create_response_event(event_type.REQ_EXTENDED, response, previous_value=previous_due_date)
    if method == response_type.LETTER:
        letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()
        letter_id = _add_letter(request_id, letter_template.title, content, event_type.EXTENSION_LETTER_CREATED)
        _create_communication_method(response.id, letter_id, response_type.LETTER)
        letter = generate_pdf(content)
        email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                      EMAIL_TEMPLATE_FOR_EVENT[event_type.EXTENSION_LETTER_CREATED])
        email_content = render_template(email_template,
                                        request_id=request_id,
                                        agency_name=request.agency.name,
                                        user=current_user
                                        )
        email_id = safely_send_and_add_email(request_id,
                                             email_content,
                                             'Request {} Extended - Letter'.format(request_id),
                                             to=get_assigned_users_emails(request_id),
                                             attachment=letter,
                                             filename=secure_filename('{}_extension_letter.pdf'.format(request_id)),
                                             mimetype='application/pdf')
        _create_communication_method(response.id, email_id, response_type.EMAIL)
    else:
        email_id = _send_response_email(request_id,
                                        privacy,
                                        content,
                                        'Request {} Extended'.format(request_id))

        _create_communication_method(response.id, email_id, response_type.EMAIL)


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


def add_response_letter(request_id, content, letter_template_id):
    """Generates a PDF response letter and emails it to the agency users.

    Args:
        request_id: Request ID
        content: HTML of the response letter
        letter_template_id: LetterTemplate ID
    """
    request = Requests.query.options(joinedload(Requests.agency)).filter_by(id=request_id).one()
    letter_template = LetterTemplates.query.filter_by(id=letter_template_id).one()
    letter_title = letter_template.title
    letter = generate_pdf(content)
    letter_id = _add_letter(request_id, letter_title, content, event_type.RESPONSE_LETTER_CREATED)
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                  EMAIL_TEMPLATE_FOR_EVENT[event_type.RESPONSE_LETTER_CREATED])
    email_content = render_template(email_template,
                                    request_id=request_id,
                                    agency_name=request.agency.name,
                                    user=current_user)
    email_id = safely_send_and_add_email(request_id,
                                         email_content,
                                         "{} Letter Added to {}".format(letter_title, request_id),
                                         to=get_assigned_users_emails(request_id),
                                         attachment=letter,
                                         filename=secure_filename('{}_{}_letter.pdf'.format(letter_title, request_id)),
                                         mimetype='application/pdf')
    _create_communication_method(letter_id, email_id, response_type.EMAIL)


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
    return response.id


def _add_letter(request_id, letter_title, letter_content, letter_type):
    """
    Create and store a letter object for the specified request.
    Stores the letter metadata in the Letters table.
    Provides parameters for the process_response function to create and store responses and events objects.

    :param request_id: FOIL Request Unique Identifier
    :param letter_content: HTML content of the letter (used to format PDF for printing)
    :param letter_type: letter type created
    :return: Response Identifier (int)
    """
    response = Letters(
        request_id,
        PRIVATE,
        letter_title,
        content=letter_content
    )
    create_object(response)
    create_response_event(letter_type, response)
    return response.id


def add_envelope(request_id, template_id, envelope_data):
    """
    Create and store an envelope object for the specified request.
    Stores the envelope LaTeX in the Letters table.

    :param request_id: FOIL Request Unique Identifier (String)
    :param template_id: ID of the template to use to generate the envelope (String)
    :param envelope_data: Dictionary of data to fill in the envelope. (EnvelopeDict)
    :return: PDF File object
    """
    request = Requests.query.options(joinedload(Requests.agency)).filter_by(id=request_id).one()

    template = '{agency_ein}/{template_name}'.format(agency_ein=request.agency.ein,
                                                     template_name=EnvelopeTemplates.query.filter_by(
                                                         id=template_id).one().template_name)

    latex = generate_envelope(template, envelope_data)

    response = Envelopes(
        request_id,
        PRIVATE,
        latex,
    )
    create_object(response)
    create_response_event(event_type.ENVELOPE_CREATED, response)
    envelope = generate_envelope_pdf(latex)
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'],
                                  EMAIL_TEMPLATE_FOR_EVENT[event_type.ENVELOPE_CREATED])
    email_content = render_template(email_template,
                                    request_id=request_id,
                                    agency_name=request.agency.name,
                                    user=current_user
                                    )
    email_id = safely_send_and_add_email(request_id,
                                         email_content,
                                         'Request {} Envelope Generated'.format(request_id),
                                         to=get_assigned_users_emails(request_id),
                                         attachment=envelope,
                                         filename=secure_filename('{}_envelope.pdf'.format(request_id)),
                                         mimetype='application/pdf')
    _create_communication_method(response.id, email_id, response_type.EMAIL)


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


def format_determination_reasons(reason_ids):
    return "|".join(Reasons.query.filter_by(id=reason_id).one().content for reason_id in reason_ids)


def _get_new_due_date(request_id, extension_length, custom_due_date, tz_name):
    """
    Gets the new due date from either generating with extension length, or setting from an inputted custom due date.
    If the extension length is -1, then we use the custom_due_date to determine the new_due_date.
    Or else, extension length has an length (20, 30, 60, 90, or 120) and new_due_date will be determined by
    generate_due_date.

    :param request_id: FOIL request ID that is being passed in to generate_new_due_date
    :param extension_length: number of days the due date is being extended by
    :param custom_due_date: custom due date of the request (string in format '%m/%d/%Y')
    :param tz_name: client's timezone name

    :return: new_due_date of the request
    """
    if extension_length == '-1':
        date = datetime.strptime(custom_due_date, '%m/%d/%Y')
        new_due_date = process_due_date(local_to_utc(date, tz_name))
    else:
        new_due_date = get_due_date(
            utc_to_local(
                Requests.query.filter_by(id=request_id).one().due_date,
                tz_name
            ),
            int(extension_length),
            tz_name)
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


def process_letter_template_request(request_id, data):
    """
    Process the letter template for the request.

    Generate a letter based on the template from the agency. Will include any headers and signatures (non-editable).
    :param request_id: FOIL Request ID
    :param data: Data from the frontend AJAX call (JSON)
    :return: the HTML of the rendered template
    """
    rtype = data['type']
    handler_for_type = {
        determination_type.ACKNOWLEDGMENT: _acknowledgment_letter_handler,
        determination_type.EXTENSION: _extension_letter_handler,
        determination_type.CLOSING: _closing_letter_handler,
        determination_type.DENIAL: _denial_letter_handler,
        determination_type.REOPENING: _reopening_letter_handler,
        response_type.LETTER: _response_letter_handler,
    }

    return handler_for_type[rtype](request_id, data)


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
            determination_type.QUICK_CLOSING: _quick_closing_email_handler,
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
    return handler_for_type[rtype](
        request_id=request_id,
        data=data,
        page=page,
        agency_name=agency_name,
        email_template=email_template)


def assign_point_of_contact(point_of_contact):
    """
    Assign a user to be the point of contact in emails/letters

    :param point_of_contact: A string containing the user_guid if point of contact has been set for a request
    :return: A User object to be designated as the point of contact for a request
    """
    if point_of_contact:
        return Users.query.filter(Users.guid == point_of_contact).one_or_none()
    else:
        return current_user


def _acknowledgment_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for an acknowledgement.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of an acknowledgement email.
    """
    acknowledgment = data.get('acknowledgment')
    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
    request = Requests.query.filter_by(id=request_id).one()

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
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                default_content=default_content,
                                                description_hidden_by_default=description_hidden_by_default,
                                                content=content,
                                                request=request,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                date=date,
                                                info=info,
                                                page=page),
                    "header": header}), 200


def _acknowledgment_letter_handler(request_id, data):
    """
    Process letter template for an acknowledgment.

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of an acknowledgment letter.
    """
    acknowledgment = data.get('acknowledgment', None)

    header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER

    request = Requests.query.filter_by(id=request_id).first()
    agency = request.agency
    agency_letter_data = agency.agency_features[response_type.LETTER]

    # Acknowledgment is only provided when getting default letter template.
    if acknowledgment is not None:
        acknowledgment = json.loads(acknowledgment)
        contents = LetterTemplates.query.filter_by(id=acknowledgment['letter_template']).first()

        if acknowledgment.get('days') == '-1':
            acknowledgment['days'] = None
            acknowledgment['date'] = local_to_utc(datetime.strptime(acknowledgment['date'], '%m/%d/%Y'),
                                                  data.get('tz_name'))
        else:
            acknowledgment['date'] = None

        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted

        letterhead = render_template_string(agency_letter_data['letterhead'])

        point_of_contact_user = assign_point_of_contact(acknowledgment.get('point_of_contact', None))

        template = render_template_string(contents.content,
                                          days=acknowledgment['days'],
                                          response_due_date=acknowledgment['date'],
                                          date=request.date_submitted,
                                          user=point_of_contact_user)

        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        return jsonify({"template": render_template('letters/base.html',
                                                    letterhead=Markup(letterhead),
                                                    signature=Markup(signature),
                                                    request=request,
                                                    date=date,
                                                    contents=Markup(template),
                                                    request_id=request_id,
                                                    footer=Markup(agency_letter_data['footer'])),
                        "header": header})
    else:
        content = data['letter_content']
        return jsonify({"template": render_template_string(content),
                        "header": header}), 200


def _extension_letter_handler(request_id, data):
    """
    Process letter template for an extension.

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of an extension letter.
    """
    extension = data.get('extension', None)

    header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER

    request = Requests.query.filter_by(id=request_id).first()
    agency = request.agency
    agency_letter_data = agency.agency_features[response_type.LETTER]

    # Extension is only provided when getting default letter template.
    if extension is not None:
        extension = json.loads(extension)
        contents = LetterTemplates.query.filter_by(id=extension['letter_template']).first()

        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted

        letterhead = render_template_string(agency_letter_data['letterhead'])

        point_of_contact_user = assign_point_of_contact(extension.get('point_of_contact', None))

        acknowledgement = request.responses.join(Determinations).filter(
            Determinations.dtype == determination_type.ACKNOWLEDGMENT).one_or_none()
        due_date = _get_new_due_date(request_id, extension['length'], extension['custom_due_date'], data['tz_name'])

        template = render_template_string(contents.content,
                                          date=request.date_submitted,
                                          user=point_of_contact_user,
                                          due_date=due_date,
                                          acknowledgement=acknowledgement
                                          )

        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        return jsonify({"template": render_template('letters/base.html',
                                                    letterhead=Markup(letterhead),
                                                    signature=Markup(signature),
                                                    request=request,
                                                    date=date,
                                                    contents=Markup(template),
                                                    request_id=request_id,
                                                    footer=Markup(agency_letter_data['footer'])),
                        "header": header})
    else:
        content = data['letter_content']
        return jsonify({"template": render_template_string(content),
                        "header": header}), 200


def _closing_letter_handler(request_id, data):
    """
    Process letter templates for a closing

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of a closing letter.
    """
    closing = data.get('closing', None)

    header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER

    request = Requests.query.filter_by(id=request_id).first()
    agency = request.agency
    agency_letter_data = agency.agency_features[response_type.LETTER]

    # Closing is only provided when getting default letter template.
    if closing is not None:
        closing = json.loads(closing)
        contents = LetterTemplates.query.filter_by(id=closing['letter_template']).first()

        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted

        letterhead = render_template_string(agency_letter_data['letterhead'])

        point_of_contact_user = assign_point_of_contact(closing.get('point_of_contact', None))

        template = render_template_string(contents.content,
                                          date=request.date_submitted,
                                          request_id=request_id,
                                          user=point_of_contact_user)

        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        return jsonify({"template": render_template('letters/base.html',
                                                    letterhead=Markup(letterhead),
                                                    signature=Markup(signature),
                                                    request=request,
                                                    date=date,
                                                    contents=Markup(template),
                                                    request_id=request_id,
                                                    footer=Markup(agency_letter_data['footer'])),
                        "header": header})
    else:
        content = data['letter_content']
        return jsonify({"template": render_template_string(content),
                        "header": header}), 200


def _denial_letter_handler(request_id, data):
    """
    Process letter templates for a denial

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of a denial letter.
    """
    denial = data.get('denial', None)

    header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER

    request = Requests.query.filter_by(id=request_id).first()
    agency = request.agency
    agency_letter_data = agency.agency_features[response_type.LETTER]

    # Denial is only provided when getting default letter template.
    if denial is not None:
        denial = json.loads(denial)
        contents = LetterTemplates.query.filter_by(id=denial['letter_template']).first()

        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted

        letterhead = render_template_string(agency_letter_data['letterhead'])

        point_of_contact_user = assign_point_of_contact(denial.get('point_of_contact', None))

        template = render_template_string(contents.content,
                                          date=request.date_submitted,
                                          request_id=request_id,
                                          user=point_of_contact_user)

        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        return jsonify({"template": render_template('letters/base.html',
                                                    letterhead=Markup(letterhead),
                                                    signature=Markup(signature),
                                                    request=request,
                                                    date=date,
                                                    contents=Markup(template),
                                                    request_id=request_id,
                                                    footer=Markup(agency_letter_data['footer'])),
                        "header": header})
    else:
        content = data['letter_content']
        return jsonify({"template": render_template_string(content),
                        "header": header}), 200


def _reopening_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for reopening a request.

    :param request_id (String): FOIL request ID
    :param data (JSON Dict): data from frontend AJAX call
    :param page (String): string url link of the request
    :param agency_name (String): string name of the agency of the request
    :param email_template (String [HTML Formatted]): raw HTML email template of a response

    :return: the HTML of the rendered email template of a reopening
    """
    reason = data.get('reason', None)
    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER

    if reason is not None:  # This means we are generating the initial email.
        default_content = True
        content = None

        date = datetime.strptime(data['date'], '%m/%d/%Y')
        reason_id = data.get('reason')
        reason = Reasons.query.filter_by(id=reason_id).one().content
        return jsonify(
            {
                "template": render_template(
                    email_template,
                    default_content=default_content,
                    content=content,
                    reason=reason,
                    request_id=request_id,
                    agency_name=agency_name,
                    date=process_due_date(local_to_utc(date, data['tz_name'])),
                    page=page),
                "header": header
            }
        ), 200
    else:  # If the reason is None, we are only rendering the final confirmation dialog.
        # TODO (@joelbcastillo): We should probably add a step parameter instead of relying on the value of the reason.
        request = Requests.query.filter_by(id=request_id).one()
        return jsonify(
            {
                "template": render_template(
                    email_template,
                    content=data['email_content'],
                    default_content=False,
                    page=page,
                    request=request,
                ),
                "header": header
            }
        ), 200


def _reopening_letter_handler(request_id, data):
    """

    Process letter templates for a re-opening

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of a re-opening letter.
    """
    header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER

    request = Requests.query.filter_by(id=request_id).first()
    agency = request.agency
    agency_letter_data = agency.agency_features[response_type.LETTER]

    # Reopening is only provided when getting default letter template.
    if data is not None:
        if data.get('letter_content', None) is not None:
            # If letter_content is provided, we are displaying confirmation dialog
            letter_content = render_template_string(data['letter_content'])
            return jsonify(
                {
                    "template": letter_content,
                    "header": header
                }
            )

        # Process the front-end information and generate the letter content

        # Retrieve letter template
        letter_template = LetterTemplates.query.filter_by(id=data['letter_template']).first()

        # Retrieve information to be filled in letter template
        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted
        point_of_contact_user = assign_point_of_contact(data.get('point_of_contact', None))
        tz_name = data.get('tz_name', current_app.config['APP_TIMEZONE'])
        due_date = _get_new_due_date(request_id, '-1', data['date'], tz_name)

        # Setup signature
        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        # Render letter components
        letterhead = render_template_string(agency_letter_data['letterhead'])
        rendered_letter_content = render_template_string(letter_template.content,
                                                         date=request.date_submitted,
                                                         due_date=due_date,
                                                         request_id=request_id,
                                                         user=point_of_contact_user)

        # Combine components and render letter
        rendered_letter = render_template('letters/base.html',
                                          letterhead=Markup(letterhead),
                                          signature=Markup(signature),
                                          request=request,
                                          date=date,
                                          contents=Markup(rendered_letter_content),
                                          request_id=request_id,
                                          footer=Markup(agency_letter_data['footer']))
        return jsonify(
            {
                "template": rendered_letter,
                "header": header
            }
        )

    else:
        return jsonify(
            {
                "error": "bad request"
            }
        ), 400


def _response_letter_handler(request_id, data):
    """
    Process letter template for a response.

    :param request_id: FOIL Request ID
    :param data: data from the frontend AJAX call
    :return: the HTML of a rendered template of a response letter.
    """
    if not eval_request_bool(data.get('confirmation', None)):
        request = Requests.query.filter_by(id=request_id).first()
        agency = request.agency
        agency_letter_data = agency.agency_features[response_type.LETTER]

        contents = LetterTemplates.query.filter_by(id=data['letter_template_id']).first()

        now = datetime.utcnow()
        date = now if now.date() > request.date_submitted.date() else request.date_submitted

        letterhead = render_template_string(agency_letter_data['letterhead'])

        point_of_contact_user = assign_point_of_contact(data.get('point_of_contact', None))

        template = render_template_string(contents.content,
                                          date_received=request.date_created,
                                          date_submitted=request.date_submitted,
                                          user=point_of_contact_user)

        if agency_letter_data['signature']['default_user_email'] is not None:
            try:
                u = find_user_by_email(agency_letter_data['signature']['default_user_email'])
            except AttributeError:
                u = current_user
                current_app.logger.exception("default_user_email: {} has not been created".format(
                    agency_letter_data['signature']['default_user_email']))
        else:
            u = current_user
        signature = render_template_string(agency_letter_data['signature']['text'], user=u, agency=agency)

        return jsonify({"template": render_template('letters/base.html',
                                                    letterhead=Markup(letterhead),
                                                    signature=Markup(signature),
                                                    request=request,
                                                    date=date,
                                                    contents=Markup(template),
                                                    request_id=request_id,
                                                    footer=Markup(agency_letter_data['footer']))
                        })
    else:
        header = CONFIRMATION_LETTER_HEADER_TO_REQUESTER
        return jsonify({"template": render_template_string(data['letter_content']),
                        "header": header}), 200


def _denial_email_handler(request_id, data, page, agency_name, email_template):
    """
    Process email template for denying a request.

    :param request_id: FOIL request ID
    :param data: data from frontend AJAX call
    :param page: string url link of the request
    :param agency_name: string name of the agency of the request
    :param email_template: raw HTML email template of a response

    :return: the HTML of the rendered template of a closing
    """
    request = Requests.query.filter_by(id=request_id).one()
    point_of_contact_user = assign_point_of_contact(data.get('point_of_contact', None))

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

    _reasons = [Reasons.query.with_entities(Reasons.title, Reasons.content, Reasons.has_appeals_language).filter_by(
        id=reason_id).one()
                for reason_id in data.getlist('reason_ids[]')]

    has_appeals_language = False
    custom_reasons = False

    reasons_text = []
    # Render the jinja for the reasons content
    for reason in _reasons:
        if reason.title == 'Denied - Reason Below':
            custom_reasons = True
            continue
        if reason.has_appeals_language:
            has_appeals_language = True
        reasons_text.append(render_template_string(reason.content, user=point_of_contact_user))

    reasons = render_template(
        os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], '_email_response_determinations_list.html'),
        reasons=reasons_text,
        custom_reasons=custom_reasons
    )

    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
    req = Requests.query.filter_by(id=request_id).one()
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
        request=req,
        agency_appeals_email=req.agency.appeals_email,
        agency_name=agency_name,
        reasons=Markup(reasons),
        page=page,
        custom_request_forms_enabled=custom_request_forms_enabled,
        description_hidden_by_default=description_hidden_by_default,
        has_appeals_language=has_appeals_language),
        "header": header
    }), 200


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
    req = Requests.query.filter_by(id=request_id).one()
    point_of_contact_user = assign_point_of_contact(data.get('point_of_contact', None))

    # Determine if custom request forms are enabled
    if 'enabled' in req.agency.agency_features['custom_request_forms']:
        custom_request_forms_enabled = req.agency.agency_features['custom_request_forms']['enabled']
    else:
        custom_request_forms_enabled = False

    # Determine if request description should be hidden when custom forms are enabled
    if 'description_hidden_by_default' in req.agency.agency_features['custom_request_forms']:
        description_hidden_by_default = req.agency.agency_features['custom_request_forms'][
            'description_hidden_by_default']
    else:
        description_hidden_by_default = False

    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
    _reasons = [Reasons.query.with_entities(Reasons.title, Reasons.content, Reasons.has_appeals_language,
                                            Reasons.type).filter_by(
        id=reason_id).one()
                for reason_id in data.getlist('reason_ids[]')]

    has_appeals_language = False
    custom_reasons = False
    denied = False

    reasons_text = []
    # Render the jinja for the reasons content
    for reason in _reasons:
        if reason.title == 'Denied - Reason Below':
            custom_reasons = True
            continue
        if reason.has_appeals_language:
            has_appeals_language = True
        if reason.type == determination_type.DENIAL:
            denied = True

        reasons_text.append(render_template_string(reason.content, user=point_of_contact_user))

    reasons = render_template(
        os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], '_email_response_determinations_list.html'),
        reasons=reasons_text,
        custom_reasons=custom_reasons
    )

    content = data['email_content'] if eval_request_bool(data['confirmation']) else None

    return jsonify({"template": render_template(
        email_template,
        content=content,
        request=req,
        agency_appeals_email=req.agency.appeals_email,
        agency_name=agency_name,
        reasons=Markup(reasons),
        page=page,
        denied=denied,
        custom_request_forms_enabled=custom_request_forms_enabled,
        description_hidden_by_default=description_hidden_by_default,
        has_appeals_language=has_appeals_language),
        "header": header
    }), 200


def _quick_closing_email_handler(request_id, data, page, agency_name, email_template):
    """Process email template for quick closing a request.

    Args:
        request_id: FOIL request ID
        data: data from frontend AJAX call
        page: string url link of the request
        agency_name: string name of the agency of the request
        email_template: raw HTML email template of a response

    Returns:
        The HTML of the rendered template of a quick closing
    """
    acknowledgment = data.get('acknowledgment')
    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
    request = Requests.query.filter_by(id=request_id).one()

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

    # Get reason text for Fulfilled via Walk In
    _reasons = Reasons.query.with_entities(Reasons.title, Reasons.content, Reasons.has_appeals_language,
                                            Reasons.type).filter_by(title='Fulfilled via Walk In').one()
    reasons_text = [_reasons.content]
    reasons = render_template(
        os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], '_email_response_determinations_list.html'),
        reasons=reasons_text
    )

    return jsonify({'template': render_template(email_template,
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                default_content=default_content,
                                                description_hidden_by_default=description_hidden_by_default,
                                                content=content,
                                                request=request,
                                                request_id=request_id,
                                                agency_name=agency_name,
                                                date=date,
                                                info=info,
                                                page=page,
                                                reasons=reasons),
                    'header': header}), 200


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
    header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
    request = Requests.query.filter_by(id=request_id).one()

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
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                default_content=default_content,
                                                description_hidden_by_default=description_hidden_by_default,
                                                content=content,
                                                request=request,
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
    request = Requests.query.filter_by(id=request_id).one()

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

    files = data.get('files')
    # if data['files'] exists, use email_content as template with specific file email template
    if files is not None:
        files = json.loads(files)
        default_content = True
        content = None
        header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
        if eval_request_bool(data['is_private']):
            email_template = 'email_templates/email_private_file_upload.html'
            header = CONFIRMATION_EMAIL_HEADER_TO_AGENCY
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
    # use default_content in response template
    else:
        default_content = False
        header = None
        content = data['email_content']
    # iterate through files dictionary to create and append links of files with privacy option of not private
    return jsonify({"template": render_template(email_template,
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                default_content=default_content,
                                                description_hidden_by_default=description_hidden_by_default,
                                                content=content,
                                                request_id=request_id,
                                                page=page,
                                                agency_name=agency_name,
                                                agency_default_email=request.agency.default_email,
                                                public_requester=request.requester.has_nyc_account,
                                                release_date=release_date,
                                                release_public_links=release_public_links,
                                                release_private_links=release_private_links,
                                                request=request,
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
    request = Requests.query.filter_by(id=request_id).one()

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

    link = data.get('link')
    # if data['link'] exists get instruction content and privacy, and render template accordingly
    if link is not None:
        link = json.loads(link)
        url = link['url']
        title = link['title']
        content = None
        privacy = link.get('privacy')
        if privacy == PRIVATE:
            header = CONFIRMATION_EMAIL_HEADER_TO_AGENCY
        else:
            header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
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
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                description_hidden_by_default=description_hidden_by_default,
                                                request=request,
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
    request = Requests.query.filter_by(id=request_id).one()

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

    note = data.get('note')
    if note is not None:
        note = json.loads(note)
        note_content = note['content']
        content = None
        privacy = note.get('privacy')
        # use private email template for note if privacy is private
        if privacy == PRIVATE:
            header = CONFIRMATION_EMAIL_HEADER_TO_AGENCY
        else:
            header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
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
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                description_hidden_by_default=description_hidden_by_default,
                                                request=request,
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
    request = Requests.query.filter_by(id=request_id).one()

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

    instruction = data.get('instruction')
    # if data['instructions'] exists get instruction content and privacy, and render template accordingly
    if instruction is not None:
        instruction = json.loads(instruction)
        instruction_content = instruction['content']
        content = None
        privacy = instruction.get('privacy')
        if privacy == PRIVATE:
            header = CONFIRMATION_EMAIL_HEADER_TO_AGENCY
        else:
            header = CONFIRMATION_EMAIL_HEADER_TO_REQUESTER
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
                                                custom_request_forms_enabled=custom_request_forms_enabled,
                                                description_hidden_by_default=description_hidden_by_default,
                                                request=request,
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
    request = Requests.query.filter_by(id=editor.response.request.id).one()
    agency_name = request.agency.name
    page = urljoin(flask_request.host_url, url_for('request.view', request_id=request.id))
    email_template = os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], "email_edit_file.html") \
        if editor.response.type == response_type.FILE \
        else os.path.join(current_app.config['EMAIL_TEMPLATE_DIR'], data['template_name'])
    email_summary_requester = None
    email_summary_edited = None
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
                'privacy') == PRIVATE and not editor.requester_viewable) and editor.response.type != response_type.FILE:
            email_template = 'email_templates/email_edit_private_response.html'
            default_content = None
        else:
            default_content = True

    # render email_template for requester if requester viewable keys are edited or privacy changed from private
    if not editor.update:
        if release_and_viewable or was_private:
            email_summary_requester = render_template(email_template,
                                                      default_content=default_content,
                                                      content=requester_content,
                                                      request_id=request.id,
                                                      agency_name=agency_name,
                                                      request=request,
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
                                               request_id=request.id,
                                               agency_name=agency_name,
                                               response=editor.response,
                                               response_data=editor,
                                               page=page,
                                               privacy=data.get('privacy'),
                                               response_privacy=response_privacy,
                                               agency=agency)
    # replace random string from request form input with html of file links generated by the server
    elif editor.update and editor.response.type == response_type.FILE:
        if requester_content is not None:
            email_summary_requester = requester_content.replace(flask_request.form['replace-string'],
                                                                render_template(
                                                                    'email_templates/edit_response_file_links.html',
                                                                    response_data=editor))
            agency = True
            default_content = True
            email_summary_edited = render_template(email_template,
                                                   default_content=default_content,
                                                   content=agency_content,
                                                   request_id=request.id,
                                                   agency_name=agency_name,
                                                   response=editor.response,
                                                   response_data=editor,
                                                   page=page,
                                                   privacy=data.get('privacy'),
                                                   response_privacy=response_privacy,
                                                   agency=agency)
        else:
            email_summary_edited = agency_content.replace(flask_request.form['replace-string'],
                                                          render_template(
                                                              'email_templates/edit_response_file_links.html',
                                                              response_data=editor,
                                                              agency=True))
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
    """Send email with file links detailing a file response has been added to the request.
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
    request = Requests.query.options(
        joinedload(Requests.requester)
    ).options(
        joinedload(Requests.agency)
    ).filter_by(id=request_id).one()
    subject = 'Response Added to {} - File'.format(request_id)
    bcc = get_assigned_users_emails(request_id)
    if release_public_links or release_private_links:
        release_date = get_release_date(datetime.utcnow(), RELEASE_PUBLIC_DAYS, tz_name).strftime("%A, %B %d, %Y")
        email_content_requester = email_content.replace(replace_string,
                                                        render_template('email_templates/response_file_links.html',
                                                                        release_public_links=release_public_links,
                                                                        release_private_links=release_private_links,
                                                                        is_anon=request.requester.is_anonymous_requester,
                                                                        release_date=release_date
                                                                        ))
        safely_send_and_add_email(request_id,
                                  email_content_requester,
                                  'Response Added to {} - File'.format(request_id),
                                  to=[request.requester.email],
                                  bcc=bcc,
                                  reply_to=request.agency.default_email)
        if private_links:
            email_content_agency = render_template('email_templates/email_private_file_upload.html',
                                                   request_id=request_id,
                                                   default_content=True,
                                                   agency_name=request.agency.name,
                                                   private_links=private_links,
                                                   page=page)
            safely_send_and_add_email(request_id,
                                      email_content_agency,
                                      'File(s) Added to {}'.format(request_id),
                                      bcc=bcc)
    elif private_links:
        email_content_agency = email_content.replace(replace_string,
                                                     render_template('email_templates/response_file_links.html',
                                                                     request_id=request_id,
                                                                     private_links=private_links,
                                                                     page=page)
                                                     )
        safely_send_and_add_email(request_id,
                                  email_content_agency,
                                  subject,
                                  bcc=bcc)


def _send_edit_response_email(request_id, email_content_agency, email_content_requester=None):
    """Sends email detailing a response has been edited.

    Always sends email to agency users on the request.
    Email is sent to requester if email_content_requester is provided.

    Args:
        request_id: Request ID
        email_content_agency: body of email being sent to agency users
        email_content_requester: body of email being sent to requester
    """
    subject = '{request_id}: Response Edited'.format(request_id=request_id)
    bcc = get_assigned_users_emails(request_id)
    request = Requests.query.options(
        joinedload(Requests.requester)
    ).options(
        joinedload(Requests.agency)
    ).filter_by(
        id=request_id).one()
    safely_send_and_add_email(request_id, email_content_agency, subject, bcc=bcc)
    if email_content_requester is not None:
        safely_send_and_add_email(request_id,
                                  email_content_requester,
                                  subject,
                                  to=[request.requester.email],
                                  reply_to=request.agency.default_email)


def _send_response_email(request_id, privacy, email_content, subject):
    """Sends an email detailing a specific response has been added to a request.

    If the response privacy is private, only agency users are emailed.
    If the response privacy is release public/private, the requester is emailed and the agency users are bcc'ed.

    Args:
        request_id: Request ID
        email_content: body of the email
        privacy: privacy of response

    Returns:
        Call safely_send_and_add_email to send email notification detailing a specific response has been added to the
        request.
    """
    bcc = get_assigned_users_emails(request_id)
    request = Requests.query.options(
        joinedload(Requests.requester)
    ).options(
        joinedload(Requests.agency)
    ).filter_by(id=request_id).one()
    kwargs = {
        'bcc': bcc,
    }
    if privacy != PRIVATE:
        kwargs['to'] = [request.requester.email]
        kwargs['reply_to'] = request.agency.default_email
    return safely_send_and_add_email(request_id,
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
        '{request_id}: Response Deleted'.format(request_id=request_id),
        to=get_assigned_users_emails(request_id))


def safely_send_and_add_email(request_id,
                              email_content,
                              subject,
                              template=None,
                              to=None,
                              bcc=None,
                              reply_to=None,
                              **kwargs):
    """Send email based on given arguments and create and store email object into the Emails table.
    Print error messages if there is Assertion or Exception error occurs.

    Args:
        request_id: FOIL request ID
        email_content: string of HTML email content that can be used as a message template
        subject: subject of the email (current is for TESTING purposes)
        template: path of the HTML template to be passed into and rendered in send_email
        to: list of person(s) email is being sent to
        bcc: list of person(s) email is being bcc'ed
        reply_to: reply-to address
    """
    try:
        send_email(subject, to=to, bcc=bcc, reply_to=reply_to, template=template, email_content=email_content, **kwargs)
        return _add_email(request_id, subject, email_content, to=to, bcc=bcc)
    except AssertionError:
        sentry.captureException()
        current_app.logger.exception('Must include: To, CC, or BCC')
    except Exception as e:
        sentry.captureException()
        current_app.logger.exception("Error: {}".format(e))


def create_response_event(events_type, response, previous_value=None, user=current_user):
    """
    Create and store event object for given response.

    :param response: response object
    :param events_type: one of app.constants.event_type
    :param previous_value: JSON to be stored in previous_value of Events (for Acknowledgements and Extensions)

    """
    event = Events(request_id=response.request_id,
                   user_guid=response.request.requester.guid if user.is_anonymous else user.guid,
                   type_=events_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id,
                   previous_value=previous_value,
                   new_value=response.val_for_events)
    # store event object
    create_object(event)


def _create_communication_method(response_id, method_id, method_type):
    """
    Create and store communication_method object for a given response.

    :param response_id: response ID
    :param method_id: response ID of the method
    :param method_type: response_type.LETTER or response_type.EMAIL
    """
    communication_method = CommunicationMethods(response_id,
                                                method_id,
                                                method_type)
    create_object(communication_method)


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
        if self.data_new.get('deleted'):
            response_type_to_event_type = {
                Files: event_type.FILE_REMOVED,
                Notes: event_type.NOTE_REMOVED,
                Links: event_type.LINK_REMOVED,
                Instructions: event_type.INSTRUCTIONS_REMOVED
            }
        else:
            response_type_to_event_type = {
                Files: event_type.FILE_EDITED,
                Notes: event_type.NOTE_EDITED,
                Links: event_type.LINK_EDITED,
                Instructions: event_type.INSTRUCTIONS_EDITED,
            }
        return response_type_to_event_type[type(self.response)]

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
                    value_orig = self._bool_check(value_orig)
                    value_new = self._bool_check(value_new)
                    self.set_data_values(field, value_orig, value_new)
        if self.data_new.get('deleted') is not None:
            self.validate_deleted()

    @staticmethod
    def _bool_check(value):
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return eval_request_bool(value)
        return value

    def validate_deleted(self) -> object:
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
                quarantine_path = os.path.join(
                    current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
                    self.response.request_id,
                    new_filename
                )
                if fu.exists(filepath) or fu.exists(quarantine_path):
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
                        sentry.captureException()
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
                        self.replace_old_file(new_filename)
                else:
                    self.errors.append(
                        "File '{}' not found.".format(new_filename))
            if self.update:
                self.handle_response_token(bool(new_filename))

    def replace_old_file(self, new_filename):
        """
        Delete old file and move new file to upload directory from quarantine directory
        """
        upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.response.request_id
        )
        quarantine_path = os.path.join(
            current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
            self.response.request_id,
            new_filename
        )
        if current_app.config['USE_VOLUME_STORAGE']:
            fu.remove(
                os.path.join(
                    upload_path,
                    self.response.name
                )
            )
            complete_upload.delay(self.response.request_id, quarantine_path, new_filename)
        elif current_app.config['USE_AZURE_STORAGE']:
            fu.azure_delete(
                os.path.join(
                    upload_path,
                    self.response.name
                )
            )
            complete_upload.delay(self.response.request_id, quarantine_path, new_filename)


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
                        {'expiration_date': calendar.addbusdays(datetime.utcnow(),
                                                                DEFAULT_RESPONSE_TOKEN_EXPIRY_DAYS)},
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
        if current_app.config['USE_VOLUME_STORAGE']:
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
        elif current_app.config['USE_AZURE_STORAGE']:
            deleted_filename = os.path.join(
                dir_deleted,
                self.response.name
            )
            current_blob_name = os.path.join(upload_path, self.response.name)
            fu.azure_copy(current_blob_name, deleted_filename)
            fu.azure_delete(
                os.path.join(
                    upload_path,
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
