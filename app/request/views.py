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
    GenerateAcknowledgmentLetterForm,
    GenerateDenialLetterForm,
    GenerateClosingLetterForm,
    GenerateEnvelopeForm,
    GenerateResponseLetterForm,
    SearchRequestsForm,
    CloseRequestForm,
    ContactAgencyForm
)
from app.request.utils import (
    create_request,
    handle_upload_no_id,
    get_address,
    send_confirmation_email,
    create_contact_record
)
from app.user_request.forms import (
    AddUserRequestForm,
    EditUserRequestForm,
    RemoveUserRequestForm,
)
from app.user_request.utils import get_current_point_of_contact

from app import sentry


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
                                        agency_ein=form.request_agency.data,
                                        upload_path=upload_path,
                                        tz_name=flask_request.form['tz-name'])
        elif current_user.is_agency:
            request_id = create_request(form.request_title.data,
                                        form.request_description.data,
                                        category=None,
                                        agency_ein=(
                                            form.request_agency.data
                                            if form.request_agency.data != 'None'
                                            else current_user.default_agency_ein),
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
                                        agency_ein=form.request_agency.data,
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


@request.route('/<request_id>', methods=['GET'])
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
        sentry.captureException()
        return abort(404)
    except AssertionError:
        print("Request belongs to inactive agency.")
        sentry.captureException()
        return abort(404)

    holidays = sorted(get_holidays_date_list(
        datetime.utcnow().year,
        (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
    )

    active_users = []
    assigned_users = []
    if current_user.is_agency:
        for agency_user in current_request.agency.active_users:
            if not agency_user in current_request.agency.administrators and (agency_user != current_user):
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
        'generate_letter': permission.GENERATE_LETTER,
        'add_user': permission.ADD_USER_TO_REQUEST,
        'edit_user': permission.EDIT_USER_REQUEST_PERMISSIONS,
        'remove_user': permission.REMOVE_USER_FROM_REQUEST,
        'edit_title': permission.EDIT_TITLE,
        'edit_title_privacy': permission.CHANGE_PRIVACY_TITLE,
        'edit_agency_request_summary': permission.EDIT_AGENCY_REQUEST_SUMMARY,
        'edit_agency_request_summary_privacy': permission.CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY,
        'edit_requester_info': permission.EDIT_REQUESTER_INFO
    }

    # Build permissions dictionary for checking on the front-end.
    for key, val in permissions.items():
        if current_user.is_anonymous or not current_request.user_requests.filter_by(
                user_guid=current_user.guid, auth_user_type=current_user.auth_user_type).first():
            permissions[key] = False
        else:
            permissions[key] = is_allowed(current_user, request_id, val) if not current_user.is_anonymous else False

    # Build dictionary of current permissions for all assigned users.
    assigned_user_permissions = {}
    for u in assigned_users:
        assigned_user_permissions[u.guid] = UserRequests.query.filter_by(
            request_id=request_id, user_guid=u.guid).one().get_permission_choice_indices()

    point_of_contact = get_current_point_of_contact(request_id)
    if point_of_contact:
        current_point_of_contact = {'user_guid': point_of_contact.user_guid}
    else:
        current_point_of_contact = {'user_guid': ''}

    # Determine if the Agency Request Summary should be shown.
    show_agency_request_summary = False

    if current_user in current_request.agency_users \
            or current_request.agency_request_summary \
            and (current_request.requester == current_user
                 and current_request.status == request_status.CLOSED
                 and not current_request.privacy['agency_request_summary']
                 or current_request.status == request_status.CLOSED
                 and current_request.agency_request_summary_release_date
                 and current_request.agency_request_summary_release_date
                 < datetime.utcnow()
                 and not current_request.privacy['agency_request_summary']):
        show_agency_request_summary = True

    # Determine if the title should be shown.
    show_title = (current_user in current_request.agency_users or
                  current_request.requester == current_user or
                  not current_request.privacy['title'])

    # Determine if "Generate Letter" functionality is enabled for the agency.

    if 'letters' in current_request.agency.agency_features:
        generate_letters_enabled = current_request.agency.agency_features['letters']['generate_letters']
    else:
        generate_letters_enabled = False

    return render_template(
        'request/view_request.html',
        request=current_request,
        status=request_status,
        agency_users=current_request.agency_users,
        edit_requester_form=EditRequesterForm(current_request.requester),
        contact_agency_form=ContactAgencyForm(current_request),
        deny_request_form=DenyRequestForm(current_request.agency.ein),
        close_request_form=CloseRequestForm(current_request.agency.ein),
        remove_user_request_form=RemoveUserRequestForm(assigned_users),
        add_user_request_form=AddUserRequestForm(active_users),
        edit_user_request_form=EditUserRequestForm(assigned_users),
        generate_acknowledgment_letter_form=GenerateAcknowledgmentLetterForm(current_request.agency.ein),
        generate_denial_letter_form=GenerateDenialLetterForm(current_request.agency.ein),
        generate_closing_letter_form=GenerateClosingLetterForm(current_request.agency.ein),
        generate_envelope_form=GenerateEnvelopeForm(current_request.agency_ein, current_request.requester),
        generate_response_letter_form=GenerateResponseLetterForm(current_request.agency.ein),
        assigned_user_permissions=assigned_user_permissions,
        current_point_of_contact=current_point_of_contact,
        holidays=holidays,
        assigned_users=assigned_users,
        active_users=active_users,
        permissions=permissions,
        show_agency_request_summary=show_agency_request_summary,
        show_title=show_title,
        is_requester=(current_request.requester == current_user),
        permissions_length=len(permission.ALL),
        generate_letters_enabled=generate_letters_enabled
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


@request.route('/contact/<request_id>', methods=['POST'])
def contact_agency(request_id):
    """
    This function handles contacting the agency about a request as a requester. 
    :return: 
    """
    current_request = Requests.query.filter_by(id=request_id).one()
    form = ContactAgencyForm(current_request)
    del form.subject
    if form.validate_on_submit():
        create_contact_record(current_request,
                              flask_request.form['first_name'],
                              flask_request.form['last_name'],
                              flask_request.form['email'],
                              "Inquiry about {}".format(request_id),
                              flask_request.form['message'])
        flash('Your message has been sent.', category='success')
    else:
        flash('There was a problem sending your message. Please try again.', category='danger')
    return redirect(url_for('request.view', request_id=request_id))
