"""
.. module:: api.request.views.

   :synopsis: Handles the API request URL endpoints for the OpenRecords application
"""

from sqlalchemy import desc
from flask import (
    jsonify,
    render_template,
    request as flask_request,
)
from datetime import datetime
from flask_login import current_user
from app.lib.date_utils import calendar
from app.request.api import request_api_blueprint
from app.lib.db_utils import update_object
from app.lib.utils import eval_request_bool
from app.lib.permission_utils import (
    is_allowed,
    get_permission
)
from app.models import Requests, Responses
from app.constants import RESPONSES_INCREMENT
from app.constants import (
    determination_type,
    response_type,
    response_privacy,
    request_status
)


@request_api_blueprint.route('/edit_privacy', methods=['GET', 'POST'])
def edit_privacy():
    """
    Edits the privacy privacy options of a request's title and agency description.
    Retrieves updated privacy options from AJAX call on view_request page and stores changes into database.

    :return: JSON Response with updated title and agency description privacy options
    """
    request_id = flask_request.form.get('id')
    current_request = Requests.query.filter_by(id=request_id).first()
    privacy = {}
    title = flask_request.form.get('title')
    agency_desc = flask_request.form.get('agency_desc')
    if title is not None:
        privacy['title'] = title == 'true'
    if agency_desc is not None:
        privacy['agency_description'] = agency_desc == 'true'
        if not privacy['agency_description']:
            release_date = calendar.addbusdays(datetime.utcnow(), offset=20)
            update_object({'privacy': privacy,
                           'agency_description_release_date': release_date},
                          Requests,
                          current_request.id)
        else:
            update_object({'privacy': privacy,
                           'agency_description_release_date': None},
                          Requests,
                          current_request.id)
        return jsonify(privacy), 200
    update_object({'privacy': privacy},
                  Requests,
                  current_request.id)
    return jsonify(privacy), 200


@request_api_blueprint.route('/view/edit', methods=['PUT'])
def edit_request_info():
    """
    Edits the title and agency description of a FOIL request through an API PUT method.
    Retrieves updated edited content from AJAX call on view_request page and stores changes into database.

    :return: JSON Response with updated content: either request title or agency description)
    """
    edit_request = flask_request.form
    # title = flask_request.form['value']
    request_id = flask_request.form.get('pk')
    current_request = Requests.query.filter_by(id=request_id).first()
    val = edit_request['value'].strip()
    update_object({edit_request['name']: val if val else None},
                  Requests,
                  current_request.id)
    return jsonify(edit_request), 200


@request_api_blueprint.route('/history', methods=['GET'])
def get_request_history():  # TODO: 2.1
    """
    Retrieves a JSON object of event objects to display the history of a request on the view request page.

    :return: json object containing list of 50 history objects from request
    """
    request_history_index = int(flask_request.form['request_history_reload_index'])
    request_history_index_end = (request_history_index + 1) * 50 + 1
    request_history = []

    for i in range(1, request_history_index_end):
        request_history.append(str(i))

    return jsonify({})


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

    responses = Responses.query.filter(
        Responses.request_id == current_request.id,
        Responses.type != response_type.EMAIL,
        Responses.deleted == False
    ).order_by(
        desc(Responses.date_modified)
    ).all()[start: start + RESPONSES_INCREMENT]

    template_path = 'request/responses/'
    response_jsons = []
    for i, response in enumerate(responses):

        # If a user is anonymous or a public user who is not the requester AND the date for Release and Public is in
        # the future, do not generate response row

        if (current_user == response.request.requester or current_user in response.request.agency_users) or (
           response.privacy != response_privacy.PRIVATE
           and response.release_date
           and response.release_date < datetime.utcnow()):
            json = {
                'id': response.id,
                'type': response.type
            }
            if eval_request_bool(flask_request.args.get('with_template')):
                row = render_template(
                    template_path + 'row.html',
                    response=response,
                    row_num=start + i + 1,
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

    return jsonify(responses=response_jsons)
