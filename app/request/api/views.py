"""
.. module:: api.request.views.

   :synopsis: Handles the API request URL endpoints for the OpenRecords application
"""

from datetime import datetime

from flask import (
    jsonify,
    render_template,
    request as flask_request,
)
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.constants import RESPONSES_INCREMENT, EVENTS_INCREMENT
from app.constants import (
    determination_type,
    event_type,
    response_type,
    response_privacy,
    request_status,
)
from app.lib.db_utils import update_object
from app.lib.permission_utils import (
    is_allowed,
    get_permission
)
from app.lib.utils import eval_request_bool
from app.models import CommunicationMethods, Requests, Responses, Events
from app.permissions.utils import get_permissions_as_list
from app.request.api import request_api_blueprint
from app.request.api.utils import create_request_info_event


@request_api_blueprint.route('/edit_privacy', methods=['GET', 'POST'])
def edit_privacy():
    """
    Edits the privacy privacy options of a request's title and agency request summary.
    Retrieves updated privacy options from AJAX call on view_request page and stores changes into database.

    :return: JSON Response with updated title and agency request summary privacy options
    """
    request_id = flask_request.form.get('id')
    current_request = Requests.query.filter_by(id=request_id).first()
    privacy = {}
    previous_value = {}
    new_value = {}
    title = flask_request.form.get('title')
    agency_request_summary = flask_request.form.get('agency_request_summary')
    type_ = ''
    if title is not None:
        privacy['title'] = title == 'true'
        previous_value['privacy'] = current_request.privacy['title']
        new_value['privacy'] = privacy['title']
        type_ = event_type.REQ_TITLE_PRIVACY_EDITED
    elif agency_request_summary is not None:
        privacy['agency_request_summary'] = agency_request_summary == 'true'
        previous_value['privacy'] = current_request.privacy['agency_request_summary']
        new_value['privacy'] = privacy['agency_request_summary']
        type_ = event_type.REQ_AGENCY_REQ_SUM_PRIVACY_EDITED
    update_object({'privacy': privacy},
                  Requests,
                  current_request.id)
    create_request_info_event(request_id,
                              type_,
                              previous_value,
                              new_value)
    return jsonify(privacy), 200


@request_api_blueprint.route('/view/edit', methods=['PUT'])
def edit_request_info():
    """
    Edits the title and agency request summary of a FOIL request through an API PUT method.
    Retrieves updated edited content from AJAX call on view_request page and stores changes into database.

    :return: JSON Response with updated content: either request title or agency request summary)
    """
    edit_request = flask_request.form
    request_id = flask_request.form.get('pk')
    current_request = Requests.query.filter_by(id=request_id).first()
    previous_value = {}
    new_value = {}
    type_ = ''
    val = edit_request['value'].strip()
    if edit_request['name'] == 'title':
        previous_value['title'] = current_request.title
        new_value['title'] = val
        type_ = event_type.REQ_TITLE_EDITED
    elif edit_request['name'] == 'agency_request_summary':
        previous_value['agency_request_summary'] = current_request.agency_request_summary
        new_value['agency_request_summary'] = val
        type_ = event_type.REQ_AGENCY_REQ_SUM_EDITED
    update_object({edit_request['name']: val if val else None},
                  Requests,
                  current_request.id)
    create_request_info_event(request_id,
                              type_,
                              previous_value,
                              new_value)
    return jsonify(edit_request), 200


@request_api_blueprint.route('/events', methods=['GET'])
@login_required
def get_request_events():
    """
    Returns a set of events (id, type, and template),
    ordered by date descending, and starting from a specific index.

    Request parameters:
    - start: (int) starting index
    - request_id: FOIL request id
    - with_template: (default: False) include html rows for each event
    """
    start = int(flask_request.args['start'])

    current_request = Requests.query.filter_by(id=flask_request.args['request_id']).one()

    events = Events.query.filter(
        Events.request_id == current_request.id,
        Events.type.in_(event_type.FOR_REQUEST_HISTORY)
    ).order_by(
        desc(Events.timestamp)
    ).all()
    total = len(events)
    events = events[start: start + EVENTS_INCREMENT]

    template_path = 'request/events/'
    event_jsons = []

    types_with_modal = [
        event_type.FILE_EDITED,
        event_type.INSTRUCTIONS_EDITED,
        event_type.LINK_EDITED,
        event_type.NOTE_EDITED,
        event_type.REQ_AGENCY_REQ_SUM_EDITED,
        event_type.REQ_AGENCY_REQ_SUM_PRIVACY_EDITED,
        event_type.REQ_TITLE_EDITED,
        event_type.REQ_TITLE_PRIVACY_EDITED,
        event_type.REQUESTER_INFO_EDITED,
        event_type.USER_PERM_CHANGED,
    ]

    for i, event in enumerate(events):
        json = {
            'id': event.id,
            'type': event.type
        }

        if eval_request_bool(flask_request.args.get('with_template')):
            has_modal = event.type in types_with_modal
            row = render_template(
                template_path + 'row.html',
                event=event,
                row_num=start + i + 1,
                has_modal=has_modal
            )
            if has_modal:
                if event.type == event_type.USER_PERM_CHANGED:
                    previous_permissions = set([
                        p.label for p in get_permissions_as_list(event.previous_value['permissions'])
                    ])
                    new_permissions = set([
                        p.label for p in get_permissions_as_list(event.new_value['permissions'])
                    ])
                    modal = render_template(
                        template_path + 'modal.html',
                        event=event,
                        modal_body=render_template(
                            "{}modal_body/{}.html".format(
                                template_path, event.type.lower()
                            ),
                            event=event,
                            permissions_granted=list(new_permissions - previous_permissions),
                            permissions_revoked=list(previous_permissions - new_permissions),
                        ),
                    )
                else:
                    modal = render_template(
                        template_path + 'modal.html',
                        modal_body=render_template(
                            "{}modal_body/{}.html".format(
                                template_path, event.type.lower()
                            ),
                            event=event
                        ),
                        event=event,
                    )
            else:
                modal = ""
            json['template'] = row + modal

        event_jsons.append(json)

    return jsonify(events=event_jsons, total=total)


@request_api_blueprint.route('/responses', methods=['GET'])
def get_request_responses():
    """
    Returns a set of responses (id, type, and template),
    ordered by date descending, and starting from a specified index.
    Request parameters:
    - start: (int) starting index
    - request_id: FOIL request id
    - with_template: (default: False) include html (rows and modals) for each response
    """
    start = int(flask_request.args['start'])

    current_request = Requests.query.filter_by(id=flask_request.args['request_id']).one()

    if current_user in current_request.agency_users:
        # If the user is an agency user assigned to the request, all responses can be retrieved.
        responses = Responses.query.filter(
            Responses.request_id == current_request.id,
            ~Responses.id.in_([cm.method_id for cm in CommunicationMethods.query.all()]),
            Responses.type != response_type.EMAIL,
            Responses.deleted == False
        ).order_by(
            desc(Responses.date_modified)
        ).all()
    elif current_user == current_request.requester:
        # If the user is the requester, then only responses that are "Release and Private" or "Release and Public"
        # can be retrieved.
        responses = Responses.query.filter(
            Responses.request_id == current_request.id,
            ~Responses.id.in_([cm.method_id for cm in CommunicationMethods.query.all()]),
            Responses.type != response_type.EMAIL,
            Responses.deleted == False,
            Responses.privacy.in_([response_privacy.RELEASE_AND_PRIVATE, response_privacy.RELEASE_AND_PUBLIC])
        ).order_by(
            desc(Responses.date_modified)
        ).all()

    else:
        # If the user is not an agency user assigned to the request or the requester, then only responses that are
        # "Release and Public" whose release date is not in the future can be retrieved.
        responses = Responses.query.filter(
            Responses.request_id == current_request.id,
            ~Responses.id.in_([cm.method_id for cm in CommunicationMethods.query.all()]),
            Responses.type != response_type.EMAIL,
            Responses.deleted == False,
            Responses.privacy.in_([response_privacy.RELEASE_AND_PUBLIC]),
            Responses.release_date.isnot(None),
            Responses.release_date < datetime.utcnow()
        ).order_by(
            desc(Responses.date_modified)
        ).all()

    total = len(responses)
    responses = responses[start: start + RESPONSES_INCREMENT]
    template_path = 'request/responses/'
    response_jsons = []
    row_count = 0
    for response in responses:
        json = {
            'id': response.id,
            'type': response.type
        }
        if eval_request_bool(flask_request.args.get('with_template')):
            row_count += 1
            row = render_template(
                template_path + 'row.html',
                response=response,
                row_num=start + row_count,
                response_type=response_type,
                determination_type=determination_type,
                show_preview=not (response.type == response_type.DETERMINATION and
                                  (response.dtype == determination_type.ACKNOWLEDGMENT or
                                   response.dtype == determination_type.REOPENING))
            )
            modal = render_template(
                template_path + 'modal.html',
                response=response,
                requires_workflow=response.type in response_type.EMAIL_WORKFLOW_TYPES,
                modal_body=render_template(
                    "{}modal_body/{}.html".format(
                        template_path, response.type
                    ),
                    response=response,
                    privacies=[response_privacy.RELEASE_AND_PUBLIC,
                               response_privacy.RELEASE_AND_PRIVATE,
                               response_privacy.PRIVATE],
                    determination_type=determination_type,
                    request_status=request_status,
                    edit_response_privacy_permission=is_allowed(user=current_user,
                                                                request_id=response.request_id,
                                                                permission=get_permission(
                                                                    permission_type='privacy',
                                                                    response_type=type(
                                                                        response))),
                    edit_response_permission=is_allowed(user=current_user,
                                                        request_id=response.request_id,
                                                        permission=get_permission(permission_type='edit',
                                                                                  response_type=type(
                                                                                      response))),
                    delete_response_permission=is_allowed(user=current_user,
                                                          request_id=response.request_id,
                                                          permission=get_permission(permission_type='delete',
                                                                                    response_type=type(response))),
                    is_editable=response.is_editable,
                    current_request=current_request

                ),
                response_type=response_type,
                determination_type=determination_type,
                request_status=request_status,
                edit_response_permission=is_allowed(user=current_user,
                                                    request_id=response.request_id,
                                                    permission=get_permission(permission_type='edit',
                                                                              response_type=type(response))),
                delete_response_permission=is_allowed(user=current_user,
                                                      request_id=response.request_id,
                                                      permission=get_permission(permission_type='delete',
                                                                                response_type=type(response))),
                edit_response_privacy_permission=is_allowed(user=current_user,
                                                            request_id=response.request_id,
                                                            permission=get_permission(
                                                                permission_type='privacy',
                                                                response_type=type(
                                                                    response))),
                is_editable=response.is_editable,
                current_request=current_request
            )
            json['template'] = row + modal

        response_jsons.append(json)

    return jsonify(responses=response_jsons, total=total)
