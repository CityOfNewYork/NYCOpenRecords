# manage.py

import sys

import os
from flask_script.commands import InvalidCommand

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*', config_file=os.path.join(os.curdir, '.coveragerc'))
    COV.start()

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db
from app.models import (
    Users,
    Agencies,
    Requests,
    Responses,
    Events,
    Reasons,
    Roles,
    UserRequests
)
from app.request.utils import (
    generate_guid
)
from app.constants import user_type_auth
from app.lib.user_information import create_mailing_address

app = create_app(os.getenv('FLASK_CONFIG') or 'default', jobs_enabled=False)
manager = Manager(app)
migrate = Migrate(app, db)


# class Celery(Command):
#     """
#     Start Celery
#     """
#
#     # TODO: autoreload and background options?
#     # http://stackoverflow.com/questions/21666229/celery-auto-reload-on-any-changes
#     # http://docs.celeryproject.org/en/latest/tutorials/daemonizing.html
#
#     def run(self):
#         subprocess.call(['celery', 'worker', '-A', 'celery_worker.celery', '--loglevel=info'])

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
        UserRequests=UserRequests
    )


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)


# manager.add_command("celery", Celery())

@manager.option('-f', '--fname', dest='first_name', default=None)
@manager.option('-l', '--lname', dest='last_name', default=None)
@manager.option('-e', '--email', dest='email', default=None)
def create_user(first_name=None, last_name=None, email=None):
    """Create an agency user."""
    if first_name is None:
        raise InvalidCommand("First name is required")

    if last_name is None:
        raise InvalidCommand("Last name is required")

    if email is None:
        raise InvalidCommand("Email is required")

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
        mailing_address=create_mailing_address(None, None, None, None)
    )
    db.session.add(user)
    db.session.commit()

    print(user)


@manager.option('-u', '--users', dest='users', action='store_true', default=False, required=False)
@manager.option('-a', '--agencies', dest='agencies', action='store_true', default=False, required=False)
@manager.option('-f', '--filename', dest='filename', default=None, required=True)
def import_data(users, agencies, filename):
    """Import data from CSV file."""
    if users:
        Users.populate(csv_name=filename)
    elif agencies:
        Agencies.populate(csv_name=filename)


@manager.option("-t", "--test-name", help="Specify tests (file, class, or specific test)", dest='test_name')
@manager.option("-c", "--coverage", help="Run coverage analysis for tests", dest='cov')
def test(cov=False, test_name=None):
    """Run the unit tests."""
    if cov and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    if not test_name:
        tests = unittest.TestLoader().discover('tests', pattern='*.py')
    else:
        tests = unittest.TestLoader().loadTestsFromName('tests.' + test_name)
    unittest.TextTestRunner(verbosity=2).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        COV.html_report()
        COV.xml_report()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import upgrade
    from app.models import Roles, Agencies, Reasons

    # migrate database to latest revision
    upgrade()

    # pre-populate
    list(map(lambda x: x.populate(), (
        Roles,
        Agencies,
        Reasons,
        Users
    )))

    es_recreate()


@manager.command
def es_recreate():
    """Recreate elasticsearch index and request docs."""
    from app.search.utils import recreate
    recreate()


@manager.command
def fix_due_dates():  # for "America/New_York"
    """
    Forgot to set due date hour to 5:00 PM in migration script before
    converting to utc. Besides having the incorrect time, this also means
    certain due dates do not fall on business days.
    """
    from app.lib.db_utils import update_object
    for request in Requests.query.all():
        update_object(
            {"due_date": request.due_date.replace(hour=22, minute=00, second=00, microsecond=00)},
            Requests,
            request.id)


@manager.command
def fix_anonymous_requesters():
    """
    Ensures there is only one anonymous requester per request by
    creating a new anonymous requester (User) for every User Requests record with
    a duplicate anonymous requester guid and updates the User Requests record.
    The new user will be identical to the existing one with the exception of the guid.
    """
    from app.constants import user_type_request
    from app.request.utils import generate_guid
    from app.lib.db_utils import create_object, update_object

    guids = db.engine.execute("""
        SELECT
          user_requests.user_guid AS "GUID"
        FROM user_requests
          JOIN users ON user_requests.user_guid = users.guid AND user_requests.auth_user_type = users.auth_user_type
        WHERE user_requests.request_user_type = 'requester'
        GROUP BY user_requests.user_guid
        HAVING COUNT(user_requests.request_id) > 1;
    """)

    for guid, in guids:
        # get all User Requests with dups, excluding the first (since we need to change all but 1)
        for ur in UserRequests.query.filter_by(
                user_guid=guid, request_user_type=user_type_request.REQUESTER
        ).offset(1):
            user = Users.query.filter_by(guid=guid, auth_user_type=user_type_auth.ANONYMOUS_USER).one()
            new_guid = generate_guid()
            print("{} -> {}".format(guid, new_guid))
            # create new anonymous requester with new guid
            create_object(
                Users(
                    guid=new_guid,
                    auth_user_type=user_type_auth.ANONYMOUS_USER,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    title=user.title,
                    organization=user.organization,
                    email_validated=False,
                    terms_of_use_accepted=False,
                    phone_number=user.phone_number,
                    fax_number=user.fax_number,
                    mailing_address=user.mailing_address
                )
            )
            # update user request with new guid
            update_object(
                {"user_guid": new_guid},
                UserRequests,
                (ur.user_guid, ur.auth_user_type, ur.request_id)
            )


@manager.command
def migrate_to_agency_request_summary():
    """
    Updates the events table in the database to use 'agency_request_summary' wherever 'agency_description' was used.
    
    """

    agency_description_types = ['request_agency_description_edited', 'request_agency_description_date_set',
                                'request_agency_description_privacy_edited']

    for event in Events.query.filter(Events.type.like('%agency_description%')).all():
        if event.type in agency_description_types:
            event.type = event.type.replace('description', 'request_summary')
        previous_value = event.previous_value

        if previous_value:
            for key in previous_value.keys():
                if key == 'agency_description':
                    previous_value['agency_request_summary'] = previous_value[key]
                    del previous_value[key]

        new_value = event.new_value
        if new_value:
            for key in new_value.keys():
                if key == 'agency_description':
                    new_value['agency_request_summary'] = new_value[key]
                    del new_value[key]

        db.session.add(event)

        request = Requests.query.filter_by(id=event.request_id).one()
        try:
            request.privacy['agency_request_summary'] = request.privacy['agency_description']
            del request.privacy['agency_description']
        except KeyError:
            pass

        db.session.add(request)
    db.session.commit()


@manager.command
def routes():
    from flask import url_for
    from urllib.parse import unquote
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            if arg == 'year':
                from datetime import datetime
                options[arg] = "{}".format(datetime.now().year)
                continue
            options[arg] = "[{}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        from datetime import datetime
        if str(datetime.now().year) in url:
            url = url.replace(str(datetime.now().year), '[year]')
        line = unquote("{:50} {:20} {}".format(rule.endpoint, methods, url))

        output.append(line)

    for line in sorted(output):
        print(line)


if __name__ == "__main__":
    try:
        manager.run()
    except InvalidCommand as err:
        print(err, file=sys.stderr)
        sys.exit(1)
