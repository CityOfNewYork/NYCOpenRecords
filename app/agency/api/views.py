from flask import (
    jsonify,
    request,
    render_template
)
from flask_login import (
    current_user,
    login_required
)
from app.agency.api import agency_api_blueprint
from app.agency.api.utils import (
    get_active_users_as_choices,
    get_letter_templates
)
from app.models import CustomRequestForms


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


@agency_api_blueprint.route('/custom_request_forms/<string:agency_ein>', methods=['GET'])
def get_custom_request_form_options(agency_ein):
    """
    Retrieve the custom request forms for the specified agency.

    :param agency_ein: Agency EIN (String)
    :return: JSON Object (keys are the id of the custom request form, values are the names of the forms)
    """
    custom_request_forms = CustomRequestForms.query.with_entities(CustomRequestForms.id,
                                                                  CustomRequestForms.form_name).filter_by(
        agency_ein=agency_ein).all()
    return jsonify(custom_request_forms), 200


@agency_api_blueprint.route('/custom_request_form_fields', methods=['GET'])
def get_custom_request_form_fields():
    """
    Get the custom request form field definitions based on form id and agency ein
    :return: JSON object containing the form field definitions
    """
    custom_request_form = CustomRequestForms.query.filter_by(id=request.args['form_id'],
                                                             agency_ein=request.args['agency_ein']).one()

    form_template = ""
    for field in custom_request_form.field_definitions:
        for key, value in field.items():
            field_text = key
            field_name = value['name']
            field_type = value['type']
            field_info = value.get('info', None)
            field_values = value.get('values', None)
            field_required = value['required']
            min_length = value.get('min_length', None)
            max_length = value.get('max_length', None)

            form_template = form_template + render_template(
                'custom_request_form_templates/{}_template.html'.format(field_type), field_text=field_text,
                field_name=field_name, field_info=field_info, options=field_values, field_required=field_required,
                min_length=min_length, max_length=max_length) + '\n'
    return jsonify(form_template), 200