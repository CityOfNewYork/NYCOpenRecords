from app.request.api import request_api_blueprint

from flask import request as flask_request, jsonify


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
