from . import agency
from flask import request
from flask_login import current_user
from app.lib.db_utils import update_object
from app.models import Agencies
from app.lib.utils import eval_request_bool


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
            return '', 200
        return '', 400
    return '', 403
