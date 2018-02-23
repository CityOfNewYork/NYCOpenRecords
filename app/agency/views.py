from datetime import datetime

from . import agency
from flask import request
from flask_login import current_user
from .utils import update_agency_active_status


# TODO: Manage agency features within this file.

@agency.route('/<agency_ein>', methods=["PATCH"])
def patch(agency_ein):
    """
    Only accessible by Super Users

    Currently only changes:
        is_active
    """
    if not current_user.is_anonymous and current_user.is_super:
        is_active = request.form.get('is_active')
        update_successful = update_agency_active_status(agency_ein, is_active)
        if update_successful:
            return '', 200
        return '', 400
    return '', 403


@agency.route('/<agency_ein>/features', methods=['GET'])
def get_agency_features(agency_ein):
    """
    Retrieve the agency features that are enabled for the specified agency.

    :param agency_ein: Agency EIN (String)

    :return: JSON Object
    """
    pass
