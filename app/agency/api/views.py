from flask import jsonify
from flask_login import current_user, login_required

from app.agency.api import agency_api_blueprint
from app.agency.api.utils import (
    get_active_users_as_choices,
    get_letter_templates
)


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


@agency_api_blueprint.route('/letter_templates/<string:agency_ein>', methods=['GET'])
@agency_api_blueprint.route('/letter_templates/<string:agency_ein>/<string:letter_type>')
@login_required
def get_agency_letter_templates(agency_ein, letter_type=None):
    """
    Retrieve letter templates for the specified agency. If letter type is provided, only those templates will be
    provided, otherwise all templates will be returned.

    :param agency_ein: Agency EIN (String)
    :param letter_type: One of "acknowledgment", "denial", "closing", "letter", "extension", "re-opening".

    :return: JSON Object (keys are template types, values are arrays of tuples (id, name))
    """
    return jsonify(get_letter_templates(agency_ein, letter_type))
