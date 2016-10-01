"""
.. module:: request.views.

   :synopsis: Handles the request URL endpoints for the OpenRecords application
"""

from flask import (
    render_template,
    request as flask_request,
    redirect,
    url_for,
)
from app.lib.user_information import create_mailing_address
from app.db_utils import get_agencies_list
from app.request import request
from .forms import (
    PublicUserRequestForm,
    AgencyUserRequestForm,
    AnonymousRequestForm
)
from .utils import create_request
from flask_login import current_user
from app.models import Requests


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
    # Public user
    if current_user.is_public:
        form = PublicUserRequestForm()
        agencies = get_agencies_list()
        form.request_agency.choices = agencies
        if flask_request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
            create_request(form.request_title.data,
                           form.request_description.data,
                           agency=form.request_agency.data,
                           upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_user.html', form=form)

    # Anonymous user
    elif current_user.is_anonymous:
        form = AnonymousRequestForm()
        agencies = get_agencies_list()
        form.request_agency.choices = agencies
        if flask_request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
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
                           address=_get_address(form),
                           upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_anon.html', form=form)

    # Agency user
    elif current_user.is_agency:
        form = AgencyUserRequestForm()
        if flask_request.method == 'POST':
            # Helper function to handle processing of data and secondary validation on the backend
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
                           address=_get_address(form),
                           upload_file=form.request_file.data)
            return redirect(url_for('main.index'))
        return render_template('request/new_request_agency.html', form=form)


def _get_address(form):
    """
    Get mailing address from form data.

    :type form: app.request.forms.AgencyUserRequestForm
                app.request.forms.AnonymousRequestForm
    """
    return create_mailing_address(
        form.address.data,
        form.city.data,
        form.state.data,
        form.zipcode.data,
        form.address_two.data or None
    )


@request.route('/view_all', methods=['GET'])
def view_all():
    return render_template('request/view_request.html')


@request.route('/view/<request_id>', methods=['GET', 'POST'])
def view(request_id):
    """
    This function is for testing purposes of the view a request back until backend functionality is implemeneted.

    :return: redirects to view_request.html which is the frame of the view a request page
    """
    request = Requests.query.filter_by(id=request_id).first()
    return render_template('request/view_request.html', request=request)
