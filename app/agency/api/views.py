from flask import jsonify
from flask_login import current_user, login_required

from app.agency.api import agency_api_blueprint
from app.agency.api.utils import get_active_users_as_choices


@agency_api_blueprint.route('/active_users/<string:agency_ein>', methods=['GET'])
@login_required
def get_active_users(agency_ein):
    """
    Retrieve the active users for the specified agency.

    :param agency_ein: Agency EIN (String)

    :return: JSON Object({"active_users": [('', 'All'), ('o8pj0k', 'John Doe')],
                          "is_admin": True}), 200
    """
    if current_user.is_agency_admin(agency_ein):
        return jsonify({"active_users": get_active_users_as_choices(agency_ein), "is_admin": True}), 200

    elif current_user.is_agency_active(agency_ein):
        active_users = [
            ('', 'All'),
            (current_user.get_id(), 'My Requests')
        ]
        return jsonify({"active_users": active_users, "is_admin": False}), 200

    else:
        return jsonify({}), 404
