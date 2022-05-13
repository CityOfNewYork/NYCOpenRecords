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
    get_letter_templates,
    get_reasons
)
from app.models import Agencies, CustomRequestForms
import json
from sqlalchemy import asc


@login_required
@agency_api_blueprint.route('/active_users/<string:agency_ein>', methods=['GET'])
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


@login_required
@agency_api_blueprint.route('/reasons/<string:agency_ein>', methods=['GET'])
@agency_api_blueprint.route('/reasons/<string:agency_ein>/<string:reason_type>', methods=['GET'])
def get_agency_reasons(agency_ein, reason_type=None):
    """Retrieve an agencies determination reasons for Denials, Closings, and Re-Openings

    Args:
        agency_ein (str): Agency EIN
        reason_type (str): One of ("denial", "closing", "re-opening")
            All other determination types do not have reasons.

    Returns:
        JSON Object (dict): Keys are the reason type, values are an array of tuples (id, title)

    """
    return jsonify(get_reasons(agency_ein, reason_type))


@login_required
@agency_api_blueprint.route('/letter_templates/<string:agency_ein>', methods=['GET'])
@agency_api_blueprint.route('/letter_templates/<string:agency_ein>/<string:letter_type>', methods=['GET'])
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
                                                                  CustomRequestForms.form_name,
                                                                  CustomRequestForms.repeatable,
                                                                  CustomRequestForms.category,
                                                                  CustomRequestForms.minimum_required).filter_by(
        agency_ein=agency_ein).order_by(asc(CustomRequestForms.category), asc(CustomRequestForms.id)).all()
    # Convert the results of with_entities back to tuple format so that jsonify can be used
    custom_request_forms = [tuple(form) for form in custom_request_forms]
    return jsonify(custom_request_forms), 200


@agency_api_blueprint.route('/custom_request_form_fields', methods=['GET'])
def get_custom_request_form_fields():
    """
    Get the custom request form field definitions based on form id and agency ein
    :return: JSON object containing the form field definitions
    """
    custom_request_form = CustomRequestForms.query.filter_by(id=request.args['form_id'],
                                                             agency_ein=request.args['agency_ein']).one()
    repeatable_counter = json.loads(request.args['repeatable_counter'])
    instance_id = custom_request_form.repeatable - repeatable_counter[str(custom_request_form.id)] + 1

    form_template = render_template('custom_request_form_templates/form_description_template.html',
                                    form_description=custom_request_form.form_description)
    data = {}
    character_counters = {}
    popovers = {}
    tooltips = {}
    error_messages = {}
    for field in custom_request_form.field_definitions:
        for key, value in field.items():
            field_text = key
            field_name = value['name']
            field_type = value['type']
            field_values = value.get('values', None)
            field_required = value.get('required', False)
            min_length = value.get('min_length', None)
            max_length = value.get('max_length', None)
            character_counter = value.get('character_counter', None)
            placeholder = value.get('placeholder', None)
            popover = value.get('popover', None)
            tooltip = value.get('tooltip', None)
            help_text = value.get('help_text', None)
            error_message = value.get('error_message', None)
            past_date_invalid = value.get('past_date_invalid', None)
            current_date_invalid = value.get('current_date_invalid', None)
            future_date_invalid = value.get('future_date_invalid', None)

            if character_counter:
                character_counter_id = field_name + "-" + str(instance_id)
                character_counters[character_counter_id] = {"min_length": min_length,
                                                            "max_length": max_length}

            if popover:
                popover_id = field_name + '-' + str(instance_id)
                popovers[popover_id] = popover

            if tooltip:
                tooltip_id = field_name + '-' + str(instance_id)
                tooltips[tooltip_id] = tooltip

            if error_message:
                error_message_id = field_name + '-' + str(instance_id)
                error_messages[error_message_id] = error_message

            form_template = form_template + render_template(
                'custom_request_form_templates/{}_template.html'.format(field_type), field_text=field_text,
                field_name=field_name, options=field_values, field_required=field_required,
                min_length=min_length, max_length=max_length, instance_id=instance_id, placeholder=placeholder,
                character_counter=character_counter, tooltip=tooltip, help_text=help_text,
                past_date_invalid=past_date_invalid, current_date_invalid=current_date_invalid,
                future_date_invalid=future_date_invalid) + '\n'
    data['form_template'] = form_template
    data['character_counters'] = character_counters
    data['popovers'] = popovers
    data['tooltips'] = tooltips
    data['error_messages'] = error_messages
    return jsonify(data), 200


@agency_api_blueprint.route('/request_types/<string:agency_ein>', methods=['GET'])
def get_request_types(agency_ein):
    """
    Retrieve the request types (custom request form names) for the specified agency.

    :param agency_ein: Agency EIN (String)

    :return: JSON Object({"request_type": [('', 'All'), ('Form Name', 'Form Name')]}), 200
    """
    if current_user.is_agency_active(agency_ein):
        agency = Agencies.query.filter_by(ein=agency_ein).one_or_none()
        if agency is not None and agency.agency_features['custom_request_forms']['enabled']:
            request_types = [
                (custom_request_form.form_name, custom_request_form.form_name)
                for custom_request_form in CustomRequestForms.query.filter_by(
                    agency_ein=agency_ein
                ).order_by(asc(CustomRequestForms.category), asc(CustomRequestForms.id)).all()
            ]
            request_types.insert(0, ("", "All"))
            return jsonify({"request_types": request_types}), 200

    return jsonify({}), 404
