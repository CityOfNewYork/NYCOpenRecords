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
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(agency=form.request_agency.data, title=form.request_title.data,
                           description=form.request_description.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_user.html', form=form)

    # Anonymous user
    if current_user and current_user.is_anonymous:
        form = AnonymousRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(agency=form.request_agency.data, title=form.request_title.data,
                           description=form.request_description.data, email=form.email.data,
                           first_name=form.first_name.data, last_name=form.last_name.data,
                           user_title=form.user_title.data, organization=form.user_organization.data,
                           phone=form.phone.data, fax=form.fax.data, address=form.address.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_anon.html', form=form)

    # Agency user
    elif current_user.is_agency:
        form = AgencyUserRequestForm()
        if request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(agency=form.request_agency.data, title=form.request_title.data,
                           description=form.request_description.data, submission=form.method_received.data,
                           agency_date_submitted=form.request_date.data, email=form.email.data,
                           first_name=form.first_name.data, last_name=form.last_name.data,
                           user_title=form.user_title.data, organization=form.user_organization.data,
                           phone=form.phone.data, fax=form.fax.data, address=form.address.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_agency.html', form=form)


@request_blueprint.route('/view', methods=['GET', 'POST'])
def view_request():
    """
    This function is for testing purposes of the view a request back until backend functionality is implemeneted.

    :return: redirects to view_request.html which is the frame of the view a request page
    """
    return render_template('request/view_request.html')
