"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import (
    render_template,
    request,
    redirect,
    url_for,
)
from app.db_utils import get_agencies_list
from app.request import request_blueprint
from app.request.forms import PublicUserRequestForm, AgencyUserRequestForm, AnonymousRequestForm
from app.request.utils import create_request
from flask_login import current_user


@request_blueprint.route('/new', methods=['GET', 'POST'])
def submit_request():
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
    # Public user
    if current_user.is_public:
        form = PublicUserRequestForm()
        agencies = get_agencies_list()
        form.request_agency.choices = agencies
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(agencies=form.request_agency.data, title=form.request_title.data,
                           description=form.request_description.data, upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_user.html', form=form)

    # Anonymous user
    if current_user and current_user.is_anonymous:
        form = AnonymousRequestForm()
        agencies = get_agencies_list()
        form.request_agency.choices = agencies
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(agencies=form.request_agency.data, title=form.request_title.data,
                           description=form.request_description.data, email=form.email.data,
                           first_name=form.first_name.data, last_name=form.last_name.data,
                           user_title=form.user_title.data, organization=form.user_organization.data,
                           phone=form.phone.data, fax=form.fax.data, address=form.address.data,
                           upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_anon.html', form=form)

    # Agency user
    elif current_user.is_agency:
        form = AgencyUserRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(title=form.request_title.data, description=form.request_description.data,
                           submission=form.method_received.data, agency_date_submitted=form.request_date.data,
                           email=form.email.data, first_name=form.first_name.data, last_name=form.last_name.data,
                           user_title=form.user_title.data, organization=form.user_organization.data,
                           phone=form.phone.data, fax=form.fax.data, address=form.address.data,
                           upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_agency.html', form=form)
