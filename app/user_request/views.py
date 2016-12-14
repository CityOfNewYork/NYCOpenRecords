"""
...module:: user_request.views.

    :synopsis: Endpoints for User Requests
"""
from app.user_request import user_request
from app.user_request.utils import remove_user_request
from app.models import Requests
from flask import (
    request as flask_request,
    flash,
    redirect,
    url_for
)
from flask_login import current_user


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
    if current_user.is_agency and current_user.is_agency_admin and current_user.agency_ein == agency_ein:
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
