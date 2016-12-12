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
    if not current_user.is_anonymous and current_user.is_agency_admin:
        form = AddAgencyUserForm(current_user.agency_ein)
        active_users = Users.query.filter(  # excluding current administrator
            Users.guid != current_user.guid,
            Users.is_agency_active == True,
            Users.agency_ein == current_user.agency_ein
        ).order_by(
            Users.last_name.desc()
        ).all()
        return render_template("admin/main.html", users=active_users, form=form)
    # JUST FOR TESTING
    # else:
    #     form = AddAgencyUserForm(3)
    #     active_users = Users.query.filter(
    #         Users.is_agency_active == True,
    #         Users.agency_ein == 3
    #     ).order_by(
    #         Users.last_name.desc()
    #     ).all()
    #     return render_template("admin/main.html", users=active_users, form=form)
    return '', 403
