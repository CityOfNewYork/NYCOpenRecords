"""
.. module:: api.request.views.

   :synopsis: Handles the API request URL endpoints for the OpenRecords application
"""

from app.request.api import request_api_blueprint
from flask import (
    jsonify,
    request as flask_request,
)
from app.lib.db_utils import update_object
from app.models import Requests
import json


@request_api_blueprint.route('/edit_visibility', methods=['GET', 'POST'])
def edit_visibility():
    """
    Edits the visibility privacy options of a request's title and agency description.
    Retrieves updated privacy options from AJAX call on view_request page and stores changes into database.

    :return: JSON Response with updated title and agency description visibility options
    """
    title = flask_request.form.get('title')
    agency_desc = flask_request.form.get('desc')
    request_id = flask_request.form.get('id')
    current_request = Requests.query.filter_by(id=request_id).first()
    # Gets request's current visibility and loads it as a string
    visibility = json.loads(current_request.visibility)
    # Stores title visibility if changed or uses current visibility if exists
    visibility['title'] = title or visibility['title']
    # Stores agency description visibility if changed or uses current visibility
    visibility['agency_description'] = agency_desc or visibility['agency_description']
    update_object(attribute='visibility',
                  value=json.dumps(visibility),
                  obj_type='Requests',
                  obj_id=current_request.id)
    return jsonify(visibility), 200


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
    update_object(attribute=edit_request['name'],
                  value=edit_request['value'],
                  obj_type='Requests',
                  obj_id=current_request.id)
    return jsonify(edit_request), 200


@request_api_blueprint.route('/history', methods=['GET', 'POST'])
def get_request_history():
    """
    Retrieves a JSON object of event objects to display the history of a request on the view request page.

    :return: json object containing list of 50 history objects from request
    """
    request_history_index = int(flask_request.form['request_history_reload_index'])
    request_history_index_end = (request_history_index + 1) * 50 + 1
    request_history = []
    # TODO: Query events table
    for i in range(1, request_history_index_end):
        request_history.append(str(i))

    return jsonify(request_history=request_history)


@request_api_blueprint.route('/responses', methods=['GET', 'POST'])
def get_request_responses():
    """
    Retrieves a JSON object of event objects to display the responses of a request on the view request page.

    :return: json object containing list of 50 response objects from request
    """
    request_responses_index = int(flask_request.form['request_responses_reload_index'])
    request_responses_index_end = (request_responses_index + 1) * 50 + 1
    request_responses = []
    # TODO: Query responses table.
    for i in range(1, request_responses_index_end):
        request_responses.append(str(i))
    return jsonify(request_responses=request_responses)
