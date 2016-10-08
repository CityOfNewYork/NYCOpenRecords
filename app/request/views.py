"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    request as flask_request,
    current_app,
    flash
)
from flask_login import current_user

from app.lib.db_utils import get_agencies_list, update_object
from app.lib.utils import InvalidUserException
from app.models import Requests
from app.request import request
from app.request.forms import (
    PublicUserRequestForm,
    AgencyUserRequestForm,
    AnonymousRequestForm
)
from flask_login import current_user
from app.models import Requests
import json
from app.request.utils import (
    create_request,
    handle_upload_no_id,
    get_address,
)
from app import recaptcha


@request.route('/new', methods=['GET', 'POST'])
def new():
    """
    Create a new FOIL request

    title: request title
    description: request description
    agency: agency selected for the request
    submission: submission method for the request

    :return: redirects to homepage if form validates
     uploaded file is stored in app/static
     if form fields are missing or has improper values, backend error messages (WTForms) will appear
    """
    site_key = current_app.config['RECAPTCHA_SITE_KEY']

    if current_user.is_public:
        form = PublicUserRequestForm()
        form.request_agency.choices = get_agencies_list()
        template_suffix = 'user.html'
    elif current_user.is_anonymous:
        form = AnonymousRequestForm()
        form.request_agency.choices = get_agencies_list()
        template_suffix = 'anon.html'
    elif current_user.is_agency:
        form = AgencyUserRequestForm()
        template_suffix = 'agency.html'
    else:
        raise InvalidUserException(current_user)

    new_request_template = 'request/new_request_' + template_suffix

    print(new_request_template)

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
            create_request(form.request_title.data,
                           form.request_description.data,
                           agency=form.request_agency.data,
                           upload_path=upload_path)
        elif current_user.is_anonymous:
            create_request(form.request_title.data,
                           form.request_description.data,
                           agency=form.request_agency.data,
                           email=form.email.data,
                           first_name=form.first_name.data,
                           last_name=form.last_name.data,
                           user_title=form.user_title.data,
                           organization=form.user_organization.data,
                           phone=form.phone.data,
                           fax=form.fax.data,
                           address=get_address(form),
                           upload_path=upload_path)
            # commented out recaptcha verifying functionalty because of NYC network proxy preventing it to send a
            # backend request to the API

            # if recaptcha.verify() is False:
            #     flash("Please complete reCAPTCHA.")
            #     return render_template(new_request_template, form=form, site_key=site_key)
        elif current_user.is_agency:
            create_request(form.request_title.data,
                           form.request_description.data,
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
                           upload_path=upload_path)
        return redirect(url_for('main.index'))
    return render_template(new_request_template, form=form, site_key=site_key)


@request.route('/view_all', methods=['GET'])
def view_all():
    return render_template('request/view_request.html')


@request.route('/view/<request_id>', methods=['GET', 'POST'])
def view(request_id):
    """
    This function is for testing purposes of the view a request back until backend functionality is implemented.

    :return: redirects to view_request.html which is the frame of the view a request page
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    visibility = json.loads(current_request.visibility)
    return render_template('request/view_request.html', request=current_request, visibility=visibility)


@request.route('/edit_visibility', methods=['GET', 'POST'])
def edit_visibility():
    """
    Edits the visibility privacy options of a request's title and agency description.
    Gets updated privacy options from AJAX call on view_request page.

    :return: JSON Response with updated title and agency description visibility options
    """
    title = flask_request.form.get('title')
    agency_desc = flask_request.form.get('desc')
    request_id = flask_request.form.get('id')
    current_request = Requests.query.filter_by(id=request_id).first()
    # Gets request's current visibility and loads it as a string
    visibility = json.loads(current_request.visibility)
    # Stores title visibility if changed or uses current visibility if exists
    visibility['title'] = title or visibility['title']
    # Stores agency description visibility if changed or uses current visibility
    visibility['agency_description'] = agency_desc or visibility['agency_description']
    update_object(attribute='visibility',
                  value=json.dumps(visibility),
                  obj_type='Requests',
                  obj_id=current_request.id)
    return jsonify(visibility), 200


@request.route('/view/edit', methods=['PUT'])
def edit_request_info():
    edit_request = flask_request.form
    # title = flask_request.form['value']
    request_id = flask_request.form.get('pk')
    current_request = Requests.query.filter_by(id=request_id).first()
    update_object(attribute=edit_request['name'],
                  value=edit_request['value'],
                  obj_type='Requests',
                  obj_id=current_request.id)
    return jsonify(edit_request), 200
