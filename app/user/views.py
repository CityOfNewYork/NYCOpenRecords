from collections import defaultdict
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user

from app.constants import (
    event_type,
    permission,
    user_attrs
)
from app.lib.db_utils import (create_object, update_object)
from app.lib.utils import eval_request_bool
from app.models import Agencies, AgencyUsers, Events, Users
from app.user import user
from app.user.utils import make_user_admin, remove_user_permissions


@user.route('/<user_id>', methods=['PATCH'])
def patch(user_id):
    """
    Request Parameters:
    - title
    - organization
    - email
    - phone_number
    - fax_number
    - mailing_address
    - is_super
    - is_agency_active
    - is_agency_admin
    (Mailing Address)
    - zip
    - city
    - state
    - address_one
    - address_two

    Restrictions:
    - Anonymous Users
        - cannot access this endpoint
    - Agency Administrators
        - cannot change their agency status
        - can only update the agency status of users within their agency
        - cannot change any super user status
    - Super Users
        - cannot change their super user status
    - Agency Users
        - cannot change any user except for themselves or
          *anonymous* requesters for requests they are assigned to
        - cannot change super user or agency status
    - Public Users
        - can only update themselves
        - cannot change super user or agency status

    """

    # Anonymous users cannot access endpoint
    if current_user.is_anonymous:
        return jsonify({'error': 'Anonymous users cannot access this endpoint'}), 403

    # Public users cannot access endpoint
    if current_user.is_public:
        return jsonify({'error': 'Public users cannot access this endpoint'}), 403

    # Unauthenticated users cannot access endpoint
    if not current_user.is_authenticated:
        return jsonify({'error': 'User must be authenticated to access endpoint'}), 403

    # Retrieve the user
    user_ = Users.query.filter_by(guid=user_id).one_or_none()

    # If the user does not exist, return 404 - Not Found
    if not user_:
        return jsonify({'error': 'Specified user does not exist.'}), 404

    # Gather Form details
    is_agency_admin = eval_request_bool(request.form.get('is_agency_admin')) if request.form.get('is_agency_admin',
                                                                                                 None) else None
    is_agency_active = eval_request_bool(request.form.get('is_agency_active')) if request.form.get('is_agency_active',
                                                                                                   None) else None
    is_super = eval_request_bool(request.form.get('is_super')) if request.form.get('is_super', None) else None

    agency_ein = request.form.get('agency_ein', None)

    # Checks that apply if user is changing their own profile
    changing_self = current_user == user_

    # Agency User Restrictions (applies to Admins and Regular Users)
    if user_.is_agency:
        # Endpoint can only be used for a specific agency
        if not agency_ein:
            return jsonify({'error': 'agency_ein must be provided to modify an agency user'}), 400

        # Agency must exist and be active to modify users
        agency = Agencies.query.filter_by(ein=agency_ein).one_or_none()
        if not agency and agency.is_active:
            return jsonify({'error': 'Agency must exist in the database and be active'}), 400

        if not current_user.is_super:
            # Current user must belong to agency specified by agency_ein
            current_user_is_agency_admin = current_user.is_agency_admin(agency.ein)

            if not current_user_is_agency_admin:
                return jsonify({'error': 'Current user must belong to agency specified by agency_ein'}), 400

            user_in_agency = AgencyUsers.query.filter(AgencyUsers.user_guid == user_.guid, AgencyUsers.agency_ein == agency_ein).one_or_none()

            if user_in_agency is None:
                return jsonify({'error': 'User to be modified must belong to agency specified by agency_ein'}), 400

        # Non-Agency Admins cannot access endpoint to modify other agency_users
        if not current_user.is_super and not current_user.is_agency_admin(agency_ein):
            return jsonify({'error': 'User must be agency admin to modify users'}), 403

        # Cannot modify super status when changing agency active or agency admin status
        if (is_agency_admin or is_agency_active) and is_super:
            return jsonify({
                'error': 'Cannot modify super status when changing agency active or agency admin status'}), 400

        if changing_self:
            # Super users cannot change their own is_super value
            if current_user.is_super and is_super:
                return jsonify({'error': 'Super users cannot change their own `super` status'}), 400

            if is_agency_admin:
                return jsonify({'error': 'Agency Administrators cannot change their administrator permissions'}), 400

    elif user_.is_public:
        if current_user != user_:
            return jsonify({'error': 'Public user attributes cannot be modified by agency users.'}), 400

    elif user_.is_anonymous_requester:
        ur = current_user.user_requests.filter_by(request_id=user_.anonymous_request.id).one_or_none()
        if not ur:
            return jsonify({
                'error': 'Agency users can only modify anonymous requesters for requests where they are assigned.'}), 403

        if not ur.has_permission(permission.EDIT_REQUESTER_INFO):
            return jsonify({'error': 'Current user does not have EDIT_REQUESTER_INFO permission'}), 403

    # Gather User Fields

    user_editable_fields = user_attrs.UserEditableFieldsDict(
        email=request.form.get('email'),
        phone_number=request.form.get('phone'),
        fax_number=request.form.get('fax'),
        title=request.form.get('title'),
        organization=request.form.get('organization'),
        address_one=request.form.get('address_one'),
        address_two=request.form.get('address_two'),
        zip=request.form.get('zipcode'),
        city=request.form.get('city'),
        state=request.form.get('state')
    )
    status_field_val = user_attrs.UserStatusDict(
        is_agency_admin=request.form.get('is_agency_admin'),
        is_agency_active=request.form.get('is_agency_active'),
        is_super=request.form.get('is_super')
    )
    if changing_self:
        if not user_editable_fields.is_valid:
            return jsonify({"error": "Missing contact information."}), 400
    else:
        if user_.is_agency and not status_field_val.is_valid:
            return jsonify({"error": "User status values invalid"}), 400

    # Status Values for Events
    old_status = {}
    new_status = {}

    # User Attributes for Events
    old_user_attrs = defaultdict(dict)
    new_user_attrs = defaultdict(dict)

    for key, value in status_field_val.items():
        if value is not None:
            if key == 'is_agency_admin':
                cur_val = user_.is_agency_admin(agency_ein)
            elif key == 'is_agency_active':
                cur_val = user_.is_agency_active(agency_ein)
            else:
                cur_val = getattr(user_, key)
            new_val = eval_request_bool(status_field_val[key])
            if cur_val != new_val:
                old_status[key] = cur_val
                new_status[key] = new_val

    for key, value in user_editable_fields.items():
        # Address is a dictionary and needs to be handled separately
        if key == 'address':
            for address_key, address_value in value.items():
                cur_val = (user_.mailing_address.get(address_key)
                           if user_.mailing_address else None)
                new_val = address_value
                if cur_val != new_val:
                    old_user_attrs['_mailing_address'][address_key] = cur_val
                    new_user_attrs['_mailing_address'][address_key] = new_val
            continue
        if value is not None:
            cur_val = getattr(user_, key)
            new_val = user_editable_fields[key]
            if cur_val != new_val:
                old_user_attrs[key] = cur_val
                new_user_attrs[key] = new_val

    # Update the Users object if new_user_attrs is not None (empty dict)
    if new_user_attrs and old_user_attrs:
        update_object(
            new_user_attrs,
            Users,
            user_id
        )
        # GUID is added to the 'new' value in events to identify the user that was changed
        new_user_attrs['user_guid'] = user_.guid

        # create event(s)
        event_kwargs = {
            'request_id': user_.anonymous_request.id if user_.is_anonymous_requester else None,
            'response_id': None,
            'user_guid': current_user.guid,
            'timestamp': datetime.utcnow()
        }

        create_object(Events(
            type_=(event_type.REQUESTER_INFO_EDITED
                   if user_.is_anonymous_requester
                   else event_type.USER_INFO_EDITED),
            previous_value=old_user_attrs,
            new_value=new_user_attrs,
            **event_kwargs
        ))

    if new_status:
        redis_key = "{current_user_guid}-{update_user_guid}-{agency_ein}-{timestamp}".format(
            current_user_guid=current_user.guid, update_user_guid=user_.guid, agency_ein=agency_ein,
            timestamp=datetime.now())
        old_status['user_guid'] = user_.guid
        new_status['user_guid'] = user_.guid

        old_status['agency_ein'] = agency_ein
        new_status['agency_ein'] = agency_ein

        # Update agency active status and create associated event. Occurs first because a user can be
        # activated / deactivated with admin status set to True.
        if is_agency_active is not None:
            update_object(
                new_status,
                AgencyUsers,
                (user_.guid, agency_ein)
            )
            event_kwargs = {
                'request_id': user_.anonymous_request.id if user_.is_anonymous_requester else None,
                'response_id': None,
                'user_guid': current_user.guid,
                'timestamp': datetime.utcnow()
            }
            if is_agency_active:
                create_object(Events(
                    type_=event_type.AGENCY_USER_ACTIVATED,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
                if is_agency_admin is not None and is_agency_admin:
                    make_user_admin.apply_async(args=(user_.guid, current_user.guid, agency_ein), task_id=redis_key)
                    return jsonify({'status': 'success', 'message': 'Update task has been scheduled.'}), 200
            else:
                create_object(Events(
                    type_=event_type.AGENCY_USER_DEACTIVATED,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
                remove_user_permissions.apply_async(
                    args=(user_.guid, current_user.guid, agency_ein, event_type.AGENCY_USER_DEACTIVATED), task_id=redis_key)
                return jsonify({'status': 'success', 'message': 'Update task has been scheduled.'}), 200
            return jsonify({'status': 'success', 'message': 'Agency user successfully updated'}), 200

        # Update agency admin status and create associated event.
        elif is_agency_admin is not None:
            new_status['agency_ein'] = agency_ein
            update_object(
                new_status,
                AgencyUsers,
                (user_.guid, agency_ein)
            )
            event_kwargs = {
                'request_id': user_.anonymous_request.id if user_.is_anonymous_requester else None,
                'response_id': None,
                'user_guid': current_user.guid,
                'timestamp': datetime.utcnow()
            }
            if is_agency_admin:
                create_object(Events(
                    type_=event_type.USER_MADE_AGENCY_ADMIN,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
                make_user_admin.apply_async(args=(user_.guid, current_user.guid, agency_ein), task_id=redis_key)
                return jsonify({'status': 'success', 'message': 'Update task has been scheduled.'}), 200
            else:
                create_object(Events(
                    type_=event_type.USER_MADE_AGENCY_USER,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
                remove_user_permissions.apply_async(
                    args=(user_.guid, current_user.guid, agency_ein, event_type.USER_MADE_AGENCY_USER), task_id=redis_key)
                return jsonify({'status': 'success', 'message': 'Update task has been scheduled.'}), 200

        # Update user super status and create associated event.
        elif is_super is not None:
            new_status['agency_ein'] = agency_ein
            update_object(
                new_status,
                AgencyUsers,
                (user_.guid, agency_ein)
            )
            event_kwargs = {
                'request_id': user_.anonymous_request.id if user_.is_anonymous_requester else None,
                'response_id': None,
                'user_guid': current_user.guid,
                'timestamp': datetime.utcnow()
            }
            if is_super:
                create_object(Events(
                    type_=event_type.USER_MADE_SUPER_USER,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
            else:
                create_object(Events(
                    type_=event_type.USER_REMOVED_FROM_SUPER,
                    previous_value=old_status,
                    new_value=new_status,
                    **event_kwargs
                ))
            return jsonify({'status': 'success', 'message': 'Agency user successfully updated'}), 200
    # Always returns 200 so that we can use the data from the response in the client side javascript
    return jsonify({'status': 'Not Modified', 'message': 'No changes detected'}), 200
