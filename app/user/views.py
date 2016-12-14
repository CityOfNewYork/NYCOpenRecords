from app.user import user
from app.models import Users
from app.constants import USER_ID_DELIMITER
from app.lib.db_utils import update_object
from flask import jsonify, request
from flask_login import current_user


@user.route('/<user_id>', methods=['PATCH'])
def patch(user_id):
    # TODO: should also handle what edit_requester_info route does
    """
    Only accessible by Agency Administrators and Super Users.

    Currently only changes:
        is_agency_admin
        is_agency_active
        is_super

    Agency Administrators cannot update themselves.
    Super Users cannot change their super user status.

    """
    if (not current_user.is_anonymous and
            (
                (current_user.is_agency_admin and current_user.is_agency_active)
                or current_user.is_super
            )):
        try:
            guid, auth_type = user_id.split(USER_ID_DELIMITER)
        except ValueError:
            return '', 400

        is_agency_admin = request.form.get('is_agency_admin')
        is_agency_active = request.form.get('is_agency_active')
        is_super = request.form.get('is_super')

        updating_self = current_user.guid == guid
        updating_super_as_super = current_user.is_super and is_super is not None
        updating_agency_as_admin = current_user.is_agency_admin and any((is_agency_admin,
                                                                         is_agency_active,
                                                                         is_super))
        if not updating_self or (updating_self
                                 and not updating_super_as_super
                                 and not updating_agency_as_admin):
            if Users.query.filter_by(
                guid=guid,
                auth_user_type=auth_type
            ).first() is not None:
                # TODO: eval_request_bool from above
                fieldnames = ['is_agency_admin', 'is_agency_active', 'is_super']
                data = {}
                for name in fieldnames:
                    val = request.form.get(name)
                    if val:
                        data[name] = val
                if data:
                    update_object(
                        data,
                        Users,
                        (guid, auth_type)
                    )
                return '', 200
            return '', 400
    return '', 403
