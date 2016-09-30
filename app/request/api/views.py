from app.request.api import request_api_blueprint

from flask import request as flask_request, jsonify


@request_api_blueprint.route('/history', methods=['GET', 'POST'])
def get_request_history():
    """
    This function is for testing ajax call for history section of the view_requests page.

    :return: list of 50 history objects from request
    """
    request_history = flask_request.form['request_history_reload_index']
    return jsonify(request_history=request_history)
