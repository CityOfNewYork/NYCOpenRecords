# manage.py
import sys
from datetime import timedelta

import os
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask_script.commands import InvalidCommand

from app import create_app, db, sentry
from app.constants import determination_type, event_type, user_type_auth
from app.lib.user_information import create_mailing_address
from app.models import (
    Agencies, AgencyUsers, CustomRequestForms, Determinations, Emails, EnvelopeTemplates, Envelopes,
    Events, LetterTemplates, Letters, Reasons, Requests, Responses, Roles, UserRequests, Users
)
from app.request.utils import generate_guid

COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage

    COV = coverage.coverage(
        branch=True, include="app/*", config_file=os.path.join(os.curdir, ".coveragerc")
    )
    COV.start()

app = create_app(os.getenv("FLASK_CONFIG") or "default")
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(
        app=app,
        db=db,
        Users=Users,
        Agencies=Agencies,
        Requests=Requests,
        Responses=Responses,
        Events=Events,
        Reasons=Reasons,
        Roles=Roles,
        UserRequests=UserRequests,
        AgencyUsers=AgencyUsers,
        Emails=Emails,
        Letters=Letters,
        LetterTemplates=LetterTemplates,
        Envelopes=Envelopes,
        EnvelopeTemplates=EnvelopeTemplates,
        CustomRequestForms=CustomRequestForms,
    )


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)


@manager.option("-f", "--fname", dest="first_name", default=None)
@manager.option("-l", "--lname", dest="last_name", default=None)
@manager.option("-e", "--email", dest="email", default=None)
@manager.option("-a", "--agency-ein", dest="ein", default=None)
@manager.option("--is-admin", dest="is_admin", default=False)
@manager.option("--is-active", dest="is_active", default=False)
def create_user(
        first_name=None,
        last_name=None,
        email=None,
        ein=None,
        is_admin=False,
        is_active=False,
):
    """Create an agency user."""
    if first_name is None:
        raise InvalidCommand("First name is required")

    if last_name is None:
        raise InvalidCommand("Last name is required")

    if email is None:
        raise InvalidCommand("Email is required")

    if ein is None:
        raise InvalidCommand("Agency EIN is required")

    user = Users(
        guid=generate_guid(),
        auth_user_type=user_type_auth.AGENCY_LDAP_USER,
        email=email,
        first_name=first_name,
        last_name=last_name,
        title=None,
        organization=None,
        email_validated=True,
        terms_of_use_accepted=True,
        phone_number=None,
        fax_number=None,
        mailing_address=create_mailing_address(None, None, None, None),
    )
    db.session.add(user)

    agency_user = AgencyUsers(
        user_guid=user.guid,
        auth_user_type=user.auth_user_type,
        agency_ein=ein,
        is_agency_active=is_active,
        is_agency_admin=is_admin,
        is_primary_agency=True,
    )
    db.session.add(agency_user)
    db.session.commit()

    print(user)


@manager.option(
    "-u", "--users", dest="users", action="store_true", default=False, required=False
)
@manager.option(
    "-a",
    "--agencies",
    dest="agencies",
    action="store_true",
    default=False,
    required=False,
)
@manager.option("-f", "--filename", dest="filename", default=None, required=True)
def import_data(users, agencies, filename):
    """Import data from CSV file."""
    if users:
        Users.populate(csv_name=filename)
    elif agencies:
        Agencies.populate(json_name=filename)


@manager.option(
    "-t",
    "--test-name",
    help="Specify tests (file, class, or specific test)",
    dest="test_name",
)
@manager.option(
    "-v", "--verbose", help="Pytest verbose mode (True/False)", dest="verbose"
)
@manager.option(
    "-c", "--coverage", help="Run coverage analysis for tests (True/False)", dest="cov"
)
def test(cov=False, test_name=None, verbose=False):
    """Run the unit tests."""
    if cov and not os.environ.get("FLASK_COVERAGE"):
        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import pytest

    command = []

    if verbose:
        command.append("-v")

    if test_name:
        command.append("tests/{test_name}".format(test_name=test_name))
    else:
        command.append("tests/")

    pytest.main(command)

    if COV:
        COV.stop()
        COV.save()
        print("Coverage Summary:")
        COV.report()
        COV.html_report()
        COV.xml_report()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware

    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app, restrictions=[length], profile_dir=profile_dir
    )
    app.run()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import upgrade

    # migrate database to latest revision
    upgrade()

    # pre-populate
    list(
        map(
            lambda x: x.populate(),
            (
                Roles,
                Agencies,
                Reasons,
                Users,
                LetterTemplates,
                EnvelopeTemplates,
                CustomRequestForms,
            ),
        )
    )

    es_recreate()


@manager.command
def es_recreate():
    """Recreate elasticsearch index and request docs."""
    from app.search.utils import recreate

    recreate()


@manager.command
def routes():
    """
    Generate a list of HTTP routes for the application.
    """
    from flask import url_for
    from urllib.parse import unquote

    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            if arg == "year":
                from datetime import datetime

                options[arg] = "{}".format(datetime.now().year)
                continue
            options[arg] = "[{}]".format(arg)

        methods = ",".join(rule.methods)
        url = url_for(rule.endpoint, **options)
        from datetime import datetime

        if str(datetime.now().year) in url:
            url = url.replace(str(datetime.now().year), "[year]")
        line = unquote("{:50} {:20} {}".format(rule.endpoint, methods, url))

        output.append(line)

    for line in sorted(output):
        print(line)

@manager.command
def migrate_nycid_users():
    """
    Migrate users to the NYC.ID v2.0 Schema
    """

    class UserNYCIDDict(dict):
        """

        """
        _keys = [
            'is_nyc_employee',
            'has_nyc_account',
            'active',
            'is_anonymous_requester'
        ]

        def __init__(self, **kwargs):
            super(UserNYCIDDict, self).__init__(self)
            self['is_nyc_employee'] = kwargs.get('is_nyc_employee')
            self['has_nyc_account'] = kwargs.get('has_nyc_account')
            self['active'] = kwargs.get('active')
            self['is_anonymous_requester'] = kwargs.get('is_anonymous_requester')

        def __setitem__(self, key, value):
            if key not in UserNYCIDDict._keys:
                raise KeyError
            dict.__setitem__(self, key, value)

    anonymous_users_updates = UserNYCIDDict(
        is_nyc_employee=False,
        has_nyc_account=False,
        active=False,
        is_anonymous_requester=True
    )

    public_users_updates = UserNYCIDDict(
        is_nyc_employee=False,
        has_nyc_account=False,
        active=False,
        is_anonymous_requester=False
    )
    agency_users_updates = UserNYCIDDict(
        is_nyc_employee=True,
        has_nyc_account=False,
        active=False,
        is_anonymous_requester=False
    )

    anon = Users.query.filter(Users.auth_user_type == user_type_auth.ANONYMOUS_USER).update(
        anonymous_users_updates, synchronize_session=False)

    public = Users.query.filter(Users.auth_user_type.in_(user_type_auth.PUBLIC_USER_TYPES)).update(
        public_users_updates, synchronize_session=False)

    agency = Users.query.filter(Users.auth_user_type.in_(user_type_auth.AGENCY_USER_TYPES)).update(
        agency_users_updates, synchronize_session=False)
    db.session.commit()

if __name__ == "__main__":
    try:
        manager.run()
    except InvalidCommand as err:
        sentry.captureException()
        print(err, file=sys.stderr)
        sys.exit(1)
