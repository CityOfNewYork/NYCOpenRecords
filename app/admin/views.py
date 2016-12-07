"""
...module:: admin.views.

    :synopsis: Endpoints for Agency Adminstrator Interface
"""
from app.admin import admin
from app.models import Users
from app.admin.forms import AddAgencyUserForm
from flask import render_template
from flask_login import current_user


@admin.route('/')
def main():
    if current_user.is_agency_admin:
        form = AddAgencyUserForm(current_user.agency_ein)
        active_users = Users.query.filter_by(
            is_agency_active=True,
            agency_ein=current_user.agency_ein)
        render_template("admin/main.html", users=active_users, form=form)
    return '', 403
