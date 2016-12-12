"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd

from sqlalchemy import any_

from flask import (
    render_template,
    redirect,
    url_for,
    request as flask_request,
    current_app,
    flash,
    Markup,
    jsonify,
)
from flask_login import current_user

from app.lib.date_utils import (
    DEFAULT_YEARS_HOLIDAY_LIST,
    get_holidays_date_list,
)
from app.lib.db_utils import (
    update_object,
)
from app.lib.utils import InvalidUserException
from app.models import (
    Requests,
    Users,
    Agencies
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
from app.constants import (
    user_type_request,
    request_status,
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
                                        form.request_category.data,
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

        if requester.email:
            flashed_message_html = render_template('request/confirmation_email.html')
            flash(Markup(flashed_message_html), category='success')
        else:
            flashed_message_html = render_template('request/confirmation_non_email.html')
            flash(Markup(flashed_message_html), category='warning')

        return redirect(url_for('request.view', request_id=request_id))
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
    current_request = Requests.query.filter_by(id=request_id).one()

    holidays = sorted(get_holidays_date_list(
        datetime.utcnow().year,
        (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
    )
    return render_template(
        'request/view_request.html',
        request=current_request,
        status=request_status,
        agency_users=current_request.agency_users,
        edit_requester_form=EditRequesterForm(current_request.requester),
        deny_request_form=DenyRequestForm(current_request.agency.ein),
        close_request_form=CloseRequestForm(current_request.agency.ein),
        holidays=holidays)


@request.route('/edit_requester_info/<request_id>', methods=['PUT'])
def edit_requester_info(request_id):
    """
    Sample Request Body
    {
        "name": "new name"
        "email": "updated@email.com"
        ...
    }
    :param request_id:
    :return:
    """
    requester = Requests.query.filter_by(id=request_id).first().requester

    user_attrs = ['email', 'phone_number', 'fax_number', 'title', 'organization']
    address_attrs = ['zip', 'city', 'state', 'address_one', 'address_two']

    user_attrs_val = {
        'email': flask_request.form.get('email') or None,  # in case of empty string
        'phone_number': flask_request.form.get('phone') or None,
        'fax_number': flask_request.form.get('fax') or None,
        'title': flask_request.form.get('title') or None,
        'organization': flask_request.form.get('organization') or None
    }

    address_attrs_val = {
        'address_one': flask_request.form.get('address_one') or None,
        'address_two': flask_request.form.get('address_two') or None,
        'zip': flask_request.form.get('zipcode') or None,
        'city': flask_request.form.get('city') or None,
        'state': flask_request.form.get('state') or None
    }

    if (user_attrs_val['email'] or
        user_attrs_val['phone_number'] or
        user_attrs_val['fax_number'] or (
            address_attrs_val['city'] and
            address_attrs_val['zip'] and
            address_attrs_val['state'] and
            address_attrs_val['address_one'])
        ):

        old = {}
        old_address = {}
        new = {}
        new_address = {}

        for attr in user_attrs:
            cur_val = getattr(requester, attr)
            new_val = user_attrs_val[attr]
            if cur_val != new_val:
                old[attr] = cur_val
                new[attr] = new_val

        for attr in address_attrs:
            cur_val = (requester.mailing_address.get(attr)
                       if requester.mailing_address else None)
            new_val = address_attrs_val[attr]
            if cur_val != new_val:
                old_address[attr] = cur_val
                new_address[attr] = new_val

        if new or new_address:
            if new_address:
                new['mailing_address'] = new_address
            update_object(new,
                          Users,
                          (requester.guid, requester.auth_user_type))

            if old_address:
                old['mailing_address'] = old_address

            response = {
                "old": old,
                "new": new
            }
        else:
            response = {"message": "No changes detected."}
        status_code = 200
    else:
        response = {"error": "Missing contact info."}
        status_code = 400

    return jsonify(response), status_code


@request.route('/agencies', methods=['GET'])
def get_agencies_as_choices():
    if flask_request.args['category']:
        # FIXME: is sorted faster than orderby?
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
