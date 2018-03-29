"""
...module:: user_request.views.

    :synopsis: Endpoints for User Requests
"""
from app.user_request import user_request
from app.user_request.utils import remove_user_request, edit_user_request, add_user_request
from app.models import Requests
from flask import (
    request as flask_request,
    flash,
    redirect,
    url_for,
    abort
)
from app.lib.utils import UserRequestException
from app.constants import permission, role_name
from flask_login import current_user
from app import sentry


@user_request.route('/<request_id>', methods=['POST'])
def create(request_id):
    """
     Creates a users permissions entry for a request and sends notification emails.

    Expects a request body containing the user's guid and new permissions.
    Ex:
    {
        'user': '7khz9y',
        1: true,
        5: false
    }
    :return:
    """
    current_user_request = current_user.user_requests.filter_by(request_id=request_id).first()
    current_request = current_user_request.request

    if (
                current_user.is_agency and (
                            current_user.is_super or
                            current_user.is_agency_admin(current_request.agency.ein) or
                        current_user_request.has_permission(permission.ADD_USER_TO_REQUEST)
            )
    ):
        user_data = flask_request.form
        point_of_contact = True if role_name.POINT_OF_CONTACT in user_data else False

        required_fields = ['user']

        for field in required_fields:
            if not user_data.get(field):
                flash('Uh Oh, it looks like the {} is missing! '
                      'This is probably NOT your fault.'.format(field), category='danger')
                return redirect(url_for('request.view', request_id=request_id))

        try:
            permissions = [int(i) for i in user_data.getlist('permission')]
            add_user_request(request_id=request_id, user_guid=user_data.get('user'),
                             permissions=permissions, point_of_contact=point_of_contact)
        except UserRequestException as e:
            sentry.captureException()
            flash(str(e), category='warning')
            return redirect(url_for('request.view', request_id=request_id))
        return redirect(url_for('request.view', request_id=request_id))
    return abort(403)


@user_request.route('/<request_id>', methods=['PATCH'])
def edit(request_id):
    """
    Updates a users permissions on a request and sends notification emails.

    Expects a request body containing the user's guid and updated permissions.
    Ex:
    {
        'user': '7khz9y',
        1: true,
        5: false
    }
    :return:
    """
    current_user_request = current_user.user_requests.filter_by(request_id=request_id).one()
    current_request = current_user_request.request

    if (
                current_user.is_agency and (
                            current_user.is_super or
                            current_user.is_agency_admin(current_request.agency.ein) or
                        current_user_request.has_permission(permission.EDIT_USER_REQUEST_PERMISSIONS)
            )
    ):
        user_data = flask_request.form
        point_of_contact = True if role_name.POINT_OF_CONTACT in user_data else False

        required_fields = ['user']

        for field in required_fields:
            if not user_data.get(field):
                flash('Uh Oh, it looks like the {} is missing! '
                      'This is probably NOT your fault.'.format(field), category='danger')
                return redirect(url_for('request.view', request_id=request_id))

        try:
            permissions = [int(i) for i in user_data.getlist('permission')]
            edit_user_request(request_id=request_id, user_guid=user_data.get('user'),
                              permissions=permissions, point_of_contact=point_of_contact)
        except UserRequestException as e:
            sentry.captureException()
            flash(e, category='warning')
            return redirect(url_for('request.view', request_id=request_id))
        return 'OK', 200
    return abort(403)


@user_request.route('/<request_id>', methods=['DELETE'])
def delete(request_id):
    """
    Removes a user from a request and send notification emails.

    Expects a request body containing user's guid and confirmation string.
    Ex:
    {
        'user': '7khz9y',
        'remove-confirmation-string': 'remove'
    }
    :return:
    """
    agency_ein = Requests.query.filter_by(id=request_id).one().agency.ein

    if (current_user.is_agency and (
                current_user.is_super or (
                        current_user.is_agency_active(agency_ein) and
                        current_user.is_agency_admin(agency_ein)
                )
            )
        ):
        user_data = flask_request.form

        required_fields = ['user',
                           'remove-confirm-string']

        # TODO: Get copy from business, insert sentry issue key in message
        # Error handling to check if retrieved elements exist. Flash error message if elements does not exist.
        for field in required_fields:
            if user_data.get(field) is None:
                flash('Uh Oh, it looks like the {} is missing! '
                      'This is probably NOT your fault.'.format(field), category='danger')
                return redirect(url_for('request.view', request_id=request_id))

        valid_confirmation_string = "REMOVE"
        if user_data['remove-confirm-string'].upper() != valid_confirmation_string:
            flash('Uh Oh, it looks like the confirmation text is incorrect! '
                  'This is probably NOT your fault.', category='danger')
            return redirect(url_for('request.view', request_id=request_id))

        remove_user_request(request_id,
                            user_data['user'])
        return '', 200
    return '', 403
