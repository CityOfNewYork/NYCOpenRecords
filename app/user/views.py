from app.user import user
from app.models import Users
from app.constants import USER_ID_DELIMITER
from app.lib.db_utils import update_object
from flask import jsonify, request


@user.route('/<user_id>', methods=['PATCH'])
def patch(user_id):  # TODO: should also handle what edit_requester_info route does
    """
    Currently only accepts agency-specific changes:
        is_agency_admin
        is_agency_active
    """
    try:
        guid, auth_type = user_id.split(USER_ID_DELIMITER)
    except ValueError:
        return '', 400

    success = False
    if Users.query.filter_by(guid=guid, auth_user_type=auth_type):
        fieldnames = ['is_agency_admin', 'is_agency_active']
        data = {}
        for name in fieldnames:
            val = request.form.get(name)
            if val:
                data[name] = val
        if data:
            success = update_object(
                data,
                Users,
                (guid, auth_type)
            )
    return jsonify({"success": success}), 200
