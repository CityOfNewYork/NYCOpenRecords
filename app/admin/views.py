"""
...module:: admin.views.

    :synopsis: Endpoints for Agency Adminstrator Interface
"""
from app.admin import admin
from app.models import Users, Agencies
from app.admin.forms import (
    SelectAgencyForm,
    ActivateAgencyUserForm
)
from flask import render_template, abort
from flask_login import current_user


@admin.route('/')
@admin.route('/<agency_ein>')
def main(agency_ein=None):
    if not current_user.is_anonymous:
        if current_user.is_super:
            agency_form = SelectAgencyForm(agency_ein)
            agency_ein = agency_ein or agency_form.agencies.choices[0][0]
            user_form = ActivateAgencyUserForm(agency_ein)
            active_users = Users.query.filter_by(
                is_agency_active=True,
                agency_ein=agency_ein
            ).order_by(
                Users.last_name.desc()
            ).all()
            agency_is_active = Agencies.query.filter_by(ein=agency_ein).one().is_active
            return render_template("admin/main.html", users=active_users,
                                   user_form=user_form, agency_form=agency_form,
                                   agency_is_active=agency_is_active)
        elif current_user.is_agency_admin and current_user.is_agency_active:
            form = ActivateAgencyUserForm(current_user.agency_ein)
            active_users = Users.query.filter(  # excluding current administrator
                Users.guid != current_user.guid,
                Users.is_agency_active == True,
                Users.agency_ein == current_user.agency_ein
            ).order_by(
                Users.last_name.desc()
            ).all()
            return render_template("admin/main.html", users=active_users, user_form=form)
    return abort(404)
