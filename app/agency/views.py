from datetime import datetime

from . import agency
from flask import request
from flask_login import current_user
from app.lib.utils import eval_request_bool
from app.lib.db_utils import update_object, create_object
from app.models import Agencies, Events
from app.constants.event_type import AGENCY_ACTIVATED


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
        if is_active is not None and Agencies.query.filter_by(
            ein=agency_ein
        ).first() is not None:
            update_object(
                {'is_active': eval_request_bool(is_active)},
                Agencies,
                agency_ein
            )
            create_object(Events(
                request_id=None,
                user_guid=current_user.guid,
                auth_user_type=current_user.auth_user_type,
                type_=AGENCY_ACTIVATED,
                new_value={"ein": agency_ein},
                timestamp=datetime.utcnow()))
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
