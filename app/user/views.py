from datetime import datetime

from flask import jsonify, request
from flask_login import current_user

from app.constants import (
    event_type,
    permission,
    role_name,
    user_type_request,
    user_attrs
)
from app.lib.db_utils import (create_object, delete_object, update_object)
from app.lib.utils import eval_request_bool
from app.models import Agencies, AgencyUsers, Events, Roles, UserRequests, Users
from app.user import user
from app.user_request.utils import create_user_request_event


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
    is_agency_admin = request.form.get('is_agency_admin')
    is_agency_active = request.form.get('is_agency_active')
    is_super = request.form.get('is_super')

    # Agency User Restrictions (applies to Admins and Regular Users)
    if user_.is_agency:
        # Endpoint can only be used for a specific agency
        agency_ein = request.form.get('agency_ein', None)
        if not agency_ein:
            return jsonify({'error': 'agency_ein must be provided to modify an agency user'}), 400

        # Agency must exist and be active to modify users
        agency = Agencies.query.filter_by(ein=agency_ein).one_or_none()
        if not agency and agency.is_active:
            return jsonify({'error': 'Agency must exist in the database and be active'}), 400

        if not current_user.is_super:
            # Current user must belong to agency specified by agency_ein
            current_user_is_agency_admin = agency_ein in [agency.ein for agency in current_user.agencies.all() if
                                                          current_user.is_agency_admin(agency.ein)]
            user_in_agency = agency_ein in [agency.ein for agency in user_.agencies.all()]
            if not current_user_is_agency_admin:
                return jsonify({'error': 'Current user must belong to agency specified by agency_ein'}), 400

            if not user_in_agency:
                return jsonify({'error': 'User to be modified must belong to agency specified by agency_ein'}), 400

        # Non-Agency Admins cannot access endpoint to modify other agency_users
        if not current_user.is_agency_admin(agency_ein) or not current_user.is_super:
            return jsonify({'error': 'User must be agency admin to modify users'}), 403

        # Only one of is_agency_admin, is_agency_active or is_super can be changed in a single operation.
        status_changes = (is_agency_active, is_agency_admin, is_super)

        if any(status_changes):
            counter = 0
            for status in status_changes:
                if status:
                    counter += 1

            if counter != 1:
                return jsonify({
                    'error': 'Only one of is_agency_admin, is_agency_active or is_super can be changed in a single operation.'}), 400

        # Checks that apply if user is changing their own profile
        changing_self = current_user == user_

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
    )
    status_field_val = user_attrs.UserStatusDict(
        is_agency_admin=request.form.get('is_agency_admin'),
        is_agency_active=request.form.get('is_agency_active'),
        is_super=request.form.get('is_super')
    )

    if not user_editable_fields.is_valid:
        return jsonify({"error": "Missing contact information."}), 400

    # Status Values for Events
    old_status = {}
    new_status = {}

    # User Attributes for Events
    old_user_attrs = {'_mailing_address': {}}
    new_user_attrs = {'_mailing_address': {}}

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
    if new_user_attrs and new_user_attrs.get('_mailing_address') and old_user_attrs:
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
        return jsonify({'success': 'User successfully updated'}), 200

    return jsonify({}), 500
    #
    #     if changing_status:
    #         if ('is_agency_admin' in new) or ('is_agency_active' in new):
    #             new['agency_ein'] = agency_ein
    #             update_object(
    #                 new,
    #                 AgencyUsers,
    #                 (user_id, agency_ein)
    #             )
    #         else:
    #             update_object(
    #                 new,
    #                 Users,
    #                 user_id
    #             )
    #
    #         new_statuses = {}
    #         old_statuses = {}
    #         for field in status_fields:
    #             if new.get(field) is not None:
    #                 new_statuses[field] = new.pop(field)
    #                 old_statuses[field] = old.pop(field)
    #
    #         # TODO: a better way to store user identifiers (than in the value columns)
    #         new_statuses['user_guid'] = user_.guid
    #         new_statuses['agency_ein'] = agency_ein
    #
    #         is_agency_active = new_statuses.get('is_agency_active')
    #         is_agency_admin = new_statuses.get('is_agency_admin')
    #
    #         # deactivate user
    #         if is_agency_active is not None and not is_agency_active:
    #             # remove ALL UserRequests
    #             for user_request in user_.user_requests.all():
    #                 create_user_request_event(event_type.USER_REMOVED, user_request)
    #                 delete_object(user_request)
    #             # update index
    #             agency = Agencies.query.filter_by(ein=agency_ein).one()
    #             for req in agency.requests:
    #                 req.es_update()
    #
    #         elif is_agency_admin is not None:
    #
    #             def set_permissions_and_create_event(user_req, perms):
    #                 """
    #                 Set permissions for a user request and create a
    #                 'user_permissions_changed' Event.
    #
    #                 :param user_req: user request
    #                 :param perms: permissions to set for user request
    #                 """
    #                 old_permissions = user_req.permissions
    #                 user_request.set_permissions(perms)
    #                 create_user_request_event(event_type.USER_PERM_CHANGED,
    #                                           user_req,
    #                                           old_permissions)
    #
    #             if is_agency_admin:
    #                 permissions = Roles.query.filter_by(name=role_name.AGENCY_ADMIN).one().permissions
    #                 # create UserRequests for ALL existing requests under user's agency where user is not assigned
    #                 # for where the user *is* assigned, only change the permissions
    #                 for req in user_.agencies.filter_by(ein=agency_ein).one().requests:
    #                     user_request = UserRequests.query.filter_by(
    #                         request_id=req.id,
    #                         user_guid=user_.guid
    #                     ).first()
    #                     if user_request is None:
    #                         user_request = UserRequests(
    #                             user_guid=user_.guid,
    #                             request_id=req.id,
    #                             request_user_type=user_type_request.AGENCY,
    #                             permissions=permissions
    #                         )
    #                         create_object(user_request)
    #                         create_user_request_event(event_type.USER_ADDED,
    #                                                   user_request)
    #                         user_request.request.es_update()
    #                     else:
    #                         set_permissions_and_create_event(user_request, permissions)
    #                         user_request.request.es_update()
    #
    #             else:
    #                 # update ALL UserRequests (strip user of permissions)
    #                 for user_request in user_.user_requests.all():
    #                     set_permissions_and_create_event(user_request, permission.NONE)
    #                     user_request.request.es_update()
    #
    #         # TODO: single email detailing user changes?
    #
    #         create_object(Events(
    #             type_=event_type.USER_STATUS_CHANGED,
    #             previous_value=old_statuses,
    #             new_value=new_statuses,
    #             **event_kwargs
    #         ))
    #
    #     if old:  # something besides status changed ('new' holds user guid and auth type)
    #
    #     return jsonify({}), 200
    # else:
    #     return jsonify({"message": "No changes detected."}), 200
