"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""
from datetime import datetime

from dateutil.relativedelta import relativedelta as rd
from flask import (
    render_template,
    redirect,
    url_for,
    request as flask_request,
    current_app,
    flash,
    Markup,
    jsonify,
    abort
)
from flask_login import current_user
from sqlalchemy import any_
from sqlalchemy.orm.exc import NoResultFound

from app.constants import (
    request_status,
    permission
)
from app.lib.date_utils import (
    DEFAULT_YEARS_HOLIDAY_LIST,
    get_holidays_date_list,
)
from app.lib.permission_utils import (
    is_allowed
)
from app.lib.utils import InvalidUserException
from app.models import (
    Requests,
    Agencies,
    UserRequests,
)
from app.request import request
from app.request.forms import (
    PublicUserRequestForm,
    AgencyUserRequestForm,
    AnonymousRequestForm,
    EditRequesterForm,
    DenyRequestForm,
    SearchRequestsForm,
    CloseRequestForm
)
from app.request.utils import (
    create_request,
    handle_upload_no_id,
    get_address,
    send_confirmation_email
)
from app.user_request.forms import (
    AddUserRequestForm,
    EditUserRequestForm,
    RemoveUserRequestForm,
)


@request.route('/new', methods=['GET', 'POST'])
def new():
    """
    Create a new FOIL request
    sends a confirmation email after the Requests object is created.

    title: request title
    description: request description
    agency: agency selected for the request
    submission: submission method for the request

    :return: redirect to homepage on successful form validation
     if form fields are missing or has improper values, backend error messages (WTForms) will appear
    """
    site_key = current_app.config['RECAPTCHA_SITE_KEY']

    if current_user.is_public:
        form = PublicUserRequestForm()
        template_suffix = 'user.html'
    elif current_user.is_anonymous:
        form = AnonymousRequestForm()
        template_suffix = 'anon.html'
    elif current_user.is_agency:
        form = AgencyUserRequestForm()
        template_suffix = 'agency.html'
    else:
        raise InvalidUserException(current_user)

    new_request_template = 'request/new_request_' + template_suffix

    if flask_request.method == 'POST':
        # validate upload with no request id available
        upload_path = None
        if form.request_file.data:
            form.request_file.validate(form)
            upload_path = handle_upload_no_id(form.request_file)
            if form.request_file.errors:
                return render_template(new_request_template, form=form, site_key=site_key)

        # create request
        if current_user.is_public:
            request_id = create_request(form.request_title.data,
                                        form.request_description.data,
                                        form.request_category.data,
                                        agency=form.request_agency.data,
                                        upload_path=upload_path,
                                        tz_name=flask_request.form['tz-name'])
        elif current_user.is_agency:
            request_id = create_request(form.request_title.data,
                                        form.request_description.data,
                                        category=None,
                                        agency=current_user.agency_ein,
                                        submission=form.method_received.data,
                                        agency_date_submitted=form.request_date.data,
                                        email=form.email.data,
                                        first_name=form.first_name.data,
                                        last_name=form.last_name.data,
                                        user_title=form.user_title.data,
                                        organization=form.user_organization.data,
                                        phone=form.phone.data,
                                        fax=form.fax.data,
                                        address=get_address(form),
                                        upload_path=upload_path,
                                        tz_name=flask_request.form['tz-name'])
        else:  # Anonymous User
            request_id = create_request(form.request_title.data,
                                        form.request_description.data,
                                        form.request_category.data,
                                        agency=form.request_agency.data,
                                        email=form.email.data,
                                        first_name=form.first_name.data,
                                        last_name=form.last_name.data,
                                        user_title=form.user_title.data,
                                        organization=form.user_organization.data,
                                        phone=form.phone.data,
                                        fax=form.fax.data,
                                        address=get_address(form),
                                        upload_path=upload_path,
                                        tz_name=flask_request.form['tz-name'])

        current_request = Requests.query.filter_by(id=request_id).first()
        requester = current_request.requester
        send_confirmation_email(request=current_request, agency=current_request.agency, user=requester)

        if current_request.agency.is_active:
            if requester.email:
                flashed_message_html = render_template('request/confirmation_email.html')
                flash(Markup(flashed_message_html), category='success')
            else:
                flashed_message_html = render_template('request/confirmation_non_email.html')
                flash(Markup(flashed_message_html), category='warning')

            return redirect(url_for('request.view', request_id=request_id))
        else:
            flashed_message_html = render_template('request/non_portal_agency_message.html',
                                                   agency=current_request.agency)
            flash(Markup(flashed_message_html), category='warning')
            return redirect(url_for('request.non_portal_agency', agency_name=current_request.agency.name))

    return render_template(new_request_template, form=form, site_key=site_key)


@request.route('/view_all', methods=['GET'])
def view_all():
    return render_template(
        'request/all.html',
        form=SearchRequestsForm(),
        holidays=sorted(get_holidays_date_list(
            datetime.utcnow().year,
            (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
        )
    )


@request.route('/view/<request_id>', methods=['GET'])
def view(request_id):
    """
    This function is for testing purposes of the view a request back until backend functionality is implemented.

    :return: redirect to view request page
    """
    try:
        current_request = Requests.query.filter_by(id=request_id).one()
        assert current_request.agency.is_active
    except NoResultFound:
        print("Request with id '{}' does not exist.".format(request_id))
        return abort(404)
    except AssertionError:
        print("Request belongs to inactive agency.")
        return abort(404)

    holidays = sorted(get_holidays_date_list(
        datetime.utcnow().year,
        (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
    )

    active_users = []
    assigned_users = []
    if current_user.is_agency:
        for agency_user in current_request.agency.active_users:
            if not agency_user.is_agency_admin and (agency_user != current_user):
                # populate list of assigned users that can be removed from a request
                if agency_user in current_request.agency_users:
                    assigned_users.append(agency_user)
                # append to list of active users that can be added to a request
                else:
                    active_users.append(agency_user)

    permissions = {
        'acknowledge': permission.ACKNOWLEDGE,
        'deny': permission.DENY,
        'extend': permission.EXTEND,
        'close': permission.CLOSE,
        're_open': permission.RE_OPEN,
        'add_file': permission.ADD_FILE,
        'edit_file_privacy': permission.EDIT_FILE_PRIVACY,
        'delete_file': permission.DELETE_FILE,
        'add_note': permission.ADD_NOTE,
        'edit_note_privacy': permission.EDIT_NOTE_PRIVACY,
        'delete_note': permission.DELETE_NOTE,
        'add_link': permission.ADD_LINK,
        'edit_link_privacy': permission.EDIT_LINK_PRIVACY,
        'delete_link': permission.DELETE_LINK,
        'add_instructions': permission.ADD_OFFLINE_INSTRUCTIONS,
        'edit_instructions_privacy': permission.EDIT_OFFLINE_INSTRUCTIONS_PRIVACY,
        'delete_instructions': permission.DELETE_OFFLINE_INSTRUCTIONS,
        'add_user': permission.ADD_USER_TO_REQUEST,
        'edit_user': permission.EDIT_USER_REQUEST_PERMISSIONS,
        'remove_user': permission.REMOVE_USER_FROM_REQUEST,
        'edit_title': permission.EDIT_TITLE,
        'edit_title_privacy': permission.CHANGE_PRIVACY_TITLE,
        'edit_agency_description': permission.EDIT_AGENCY_DESCRIPTION,
        'edit_agency_description_privacy': permission.CHANGE_PRIVACY_AGENCY_DESCRIPTION,
        'edit_requester_info': permission.EDIT_REQUESTER_INFO
    }

    for key, val in permissions.items():
        if current_user.is_anonymous or not current_request.user_requests.filter_by(
                user_guid=current_user.guid, auth_user_type=current_user.auth_user_type).first():
            permissions[key] = False
        else:
            permissions[key] = is_allowed(current_user, request_id, val) if not current_user.is_anonymous else False

    assigned_user_permissions = {}
    for u in assigned_users:
        assigned_user_permissions[u.guid] = UserRequests.query.filter_by(
            request_id=request_id, user_guid=u.guid).one().get_permissions()

    show_agency_description = False
    if (
        current_user in current_request.agency_users or
        current_request.requester is current_user or
        (
            current_request.agency_description_release_date and
            current_request.agency_description_release_date < datetime.utcnow() and not
            current_request.privacy['agency_description']
        )
    ):
        show_agency_description = True
    return render_template(
        'request/view_request.html',
        request=current_request,
        status=request_status,
        agency_users=current_request.agency_users,
        edit_requester_form=EditRequesterForm(current_request.requester),
        deny_request_form=DenyRequestForm(current_request.agency.ein),
        close_request_form=CloseRequestForm(current_request.agency.ein),
        remove_user_request_form=RemoveUserRequestForm(assigned_users),
        add_user_request_form=AddUserRequestForm(active_users),
        edit_user_request_form=EditUserRequestForm(assigned_users),
        assigned_user_permissions=assigned_user_permissions,
        holidays=holidays,
        assigned_users=assigned_users,
        active_users=active_users,
        permissions=permissions,
        show_agency_description=show_agency_description,
        is_requester=(current_request.requester == current_user),
        permissions_length=len(permission.ALL)
    )


@request.route('/non_portal_agency/<agency_name>', methods=['GET'])
def non_portal_agency(agency_name):
    """
    This function handles messaging to the requester if they submitted a request to a non-portal agency.

    :return: redirect to non_portal_agency page.
    """
    return render_template('request/non_partner_request.html', agency_name=agency_name)


@request.route('/agencies', methods=['GET'])
def get_agencies_as_choices():
    """
    Get selected category value from the request body and generate a list of sorted agencies from the category.

    :return: list of agency choices
    """
    if flask_request.args['category']:
        # TODO: is sorted faster than orderby?
        choices = sorted(
            [(agencies.ein, agencies.name)
             for agencies in Agencies.query.filter(
                flask_request.args['category'] == any_(Agencies.categories)
            ).all()],
            key=lambda x: x[1])
    else:
        choices = sorted(
            [(agencies.ein, agencies.name)
             for agencies in Agencies.query.all()],
            key=lambda x: x[1])
    return jsonify(choices)
