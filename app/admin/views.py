"""
...module:: admin.views.

    :synopsis: Endpoints for Agency Adminstrator Interface
"""
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user
from sqlalchemy import func

from app.admin import admin
from app.admin.forms import (
    AddAgencyUserForm,
    ActivateAgencyUserForm,
    SelectAgencyForm,
)
from app.admin.utils import get_agency_active_users
from app.constants import OPENRECORDS_DL_EMAIL
from app.lib.db_utils import create_object
from app.lib.email_utils import (
    get_agency_admin_emails,
    send_email,
)
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
            return render_template('admin/main.html',
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
                return render_template('admin/main.html',
                                       agency_ein=agency_ein,
                                       users=active_users,
                                       agency_form=agency_form,
                                       user_form=form,
                                       multi_agency_admin=True)
            return render_template('admin/main.html',
                                   users=active_users,
                                   agency_ein=agency_ein,
                                   user_form=form)

    return abort(404)


@admin.route('/add-user', methods=['GET', 'POST'])
@has_super()
def add_user():
    """Adds a user to the users and agency_users tables.

    Returns:
        Template with context.
    """
    form = AddAgencyUserForm()

    if form.validate_on_submit():
        agency_ein = form.agency.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data

        user = Users.query.filter(
            func.lower(Users.email) == email.lower(),
            Users.is_nyc_employee == True
        ).first()

        if user is not None:
            flash('{} {} has already been added.'.format(first_name, last_name), category='warning')
        else:
            new_user = Users(
                guid=generate_guid(),
                first_name=first_name,
                last_name=last_name,
                email=email,
                email_validated=False,
                is_nyc_employee=True,
                is_anonymous_requester=False,
            )
            create_object(new_user)

            agency_user = AgencyUsers(
                user_guid=new_user.guid,
                agency_ein=agency_ein,
                is_agency_active=False,
                is_agency_admin=False,
                is_primary_agency=True
            )
            create_object(agency_user)

            agency = Agencies.query.filter_by(ein=agency_ein).one()
            admin_emails = get_agency_admin_emails(agency)
            send_email(
                subject='User {} Added'.format(new_user.fullname),
                to=admin_emails,
                template='email_templates/email_agency_user_added',
                agency_name=agency.name,
                name=new_user.fullname,
            )

            content_id = 'login_screenshot'
            image = {'path': current_app.config['LOGIN_IMAGE_PATH'],
                     'content_id': content_id}
            send_email(
                subject='OpenRecords Portal',
                to=[new_user.email],
                email_content=render_template('email_templates/email_user_added.html',
                                              agency_name=agency.name,
                                              content_id=content_id,
                                              domain=new_user.email.split('@')[1],
                                              name=new_user.fullname),
                image=image
            )

            send_email(
                subject='User {} Added'.format(new_user.fullname),
                to=[OPENRECORDS_DL_EMAIL],
                email_content='{} has been added to OpenRecords. Add {} to the service desk.'.format(
                    new_user.fullname, new_user.email)
            )

            flash('{} has been added.'.format(new_user.fullname), category='success')
        return redirect(url_for('admin.add_user'))

    return render_template('admin/add_user.html',
                           form=form)
