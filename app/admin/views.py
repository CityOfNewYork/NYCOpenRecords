"""
...module:: admin.views.

    :synopsis: Endpoints for Agency Adminstrator Interface
"""
from app.admin import admin
from app.models import Users, Agencies, AgencyUsers
from app.admin.forms import (
    SelectAgencyForm,
    ActivateAgencyUserForm
)
from flask import render_template, abort
from flask_login import current_user
from app.constants import user_type_auth
from app.admin.utils import get_agency_active_users


# TODO: View function to handle updates to agency wide settings (see models.py:183


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
