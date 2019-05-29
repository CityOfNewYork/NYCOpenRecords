"""
...module:: admin.views.

    :synopsis: Endpoints for Agency Adminstrator Interface
"""
from flask import render_template, abort
from flask_login import current_user

from app.admin import admin
from app.admin.forms import (
    AddAgencyUserForm,
    ActivateAgencyUserForm,
    SelectAgencyForm,
)
from app.admin.utils import get_agency_active_users
from app.lib.db_utils import create_object
from app.lib.email_utils import send_email
from app.lib.permission_utils import has_super
from app.models import (
    Agencies,
    AgencyUsers,
    Users,
)
from app.request.utils import generate_guid


# TODO: View function to handle updates to agency wide settings (see models.py:183)


@admin.route('/')
@admin.route('/<agency_ein>')
def main(agency_ein=None):
    if not current_user.is_anonymous:
        if agency_ein is None:
            agency_ein = current_user.find_admin_agency_ein
        if current_user.is_super:
            agency_form = SelectAgencyForm(agency_ein)
            agency_ein = agency_ein or agency_form.agencies.choices[0][0]
            user_form = ActivateAgencyUserForm(agency_ein)
            active_users = get_agency_active_users(agency_ein)
            agency_is_active = Agencies.query.filter_by(ein=agency_ein).one().is_active
            return render_template("admin/main.html",
                                   agency_ein=agency_ein,
                                   users=active_users,
                                   user_form=user_form,
                                   agency_form=agency_form,
                                   agency_is_active=agency_is_active)
        elif current_user.is_agency_admin(agency_ein) and current_user.is_agency_active(agency_ein):
            form = ActivateAgencyUserForm(agency_ein)
            active_users = get_agency_active_users(agency_ein)
            del active_users[active_users.index(current_user)]
            if len(current_user.agencies.all()) > 1:
                agency_form = SelectAgencyForm(agency_ein)
                return render_template("admin/main.html",
                                       agency_ein=agency_ein,
                                       users=active_users,
                                       agency_form=agency_form,
                                       user_form=form,
                                       multi_agency_admin=True)
            return render_template("admin/main.html",
                                   users=active_users,
                                   agency_ein=agency_ein,
                                   user_form=form)

    return abort(404)


@admin.route('/add-user', methods=['GET', 'POST'])
@has_super()
def add_user():
    form = AddAgencyUserForm()
    if form.validate_on_submit():
        agency_ein = form.agency.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data

        user = Users(
            guid=generate_guid(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            email_validated=False,
            is_nyc_employee=True,
            is_anonymous_requester=False,
        )
        create_object(user)

        agency_user = AgencyUsers(
            user_guid=user.guid,
            agency_ein=agency_ein,
            is_agency_active=False,
            is_agency_admin=False,
            is_primary_agency=True
        )
        create_object(agency_user)

    return render_template("admin/add_user.html",
                           form=form)
