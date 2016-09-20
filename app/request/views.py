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

import os
from app.request import request_blueprint
from app.request.forms import PublicUserRequestForm, AgencyUserRequestForm, AnonymousRequestForm
from app.request.utils import process_request, process_anon_request, process_agency_request


@request_blueprint.route('/new/<string:user_type>', methods=['GET', 'POST'])
def create_request(user_type):
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
    if user_type == 'public':
        form = PublicUserRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            process_request(agency=form.request_agency.data, title=form.request_title.data,
                            description=form.request_description.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_user.html', form=form)

    # Anonymous user
    elif user_type == 'anon':
        form = AnonymousRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            process_anon_request(agency=form.request_agency.data,title=form.request_title.data,
                                 description=form.request_description.data, email=form.email.data,
                                 first_name=form.first_name.data, last_name=form.last_name.data,
                                 user_title=form.user_title.data, company=form.user_organization.data,
                                 phone=form.phone.data, fax=form.fax.data, address=form.address.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request-anon.html', form=form)

    # Agency user
    elif user_type == 'agency':
        form = AgencyUserRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            process_agency_request(agency=form.request_agency.data,title=form.request_title.data,
                                   description=form.request_description.data, submission=form.method_received.data,
                                   email=form.email.data, first_name=form.first_name.data,
                                   last_name=form.last_name.data, user_title=form.user_title.data,
                                   company=form.user_organization.data, phone=form.phone.data, fax=form.fax.data,
                                   address=form.address.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_agency.html', form=form)
