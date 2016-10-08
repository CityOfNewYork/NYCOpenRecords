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
from app.request import request
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
