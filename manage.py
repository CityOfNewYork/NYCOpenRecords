# manage.py

import os
import subprocess

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*', config_file=os.path.join(os.curdir, '.coveragerc'))
    COV.start()

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell, Command

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

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)

#
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


@manager.option("-t", "--test-name", help="Specify tests (file, class, or specific test)", dest='test_name')
@manager.option("-c", "--coverage", help="Run coverage analysis for tests", dest='coverage')
def test(coverage=False, test_name=None):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
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
    # create_users()


@manager.command
def es_recreate():
    """Recreate elasticsearch index and request docs."""
    from app.search.utils import recreate
    recreate()


@manager.command
def create_search_set():
    """Create a number of requests for test purposes."""
    from tests.lib.tools import create_requests_search_set
    from app.constants.user_type_auth import PUBLIC_USER_TYPES
    import random

    users = random.sample(PUBLIC_USER_TYPES, 2)
    for i in enumerate(users):
        users[i[0]] = Users.query.filter_by(auth_user_type=users[i[0]]).first()

    create_requests_search_set(users[0], users[1])


@manager.command
def create_users():
    """Create a user from each of the allowed auth_user_types."""
    from app.constants.user_type_auth import PUBLIC_USER_TYPES
    types = [type_ for type_ in PUBLIC_USER_TYPES]

    from tests.lib.tools import create_user
    for type_ in types:
        user = create_user(type_)
        print("Created User: {guid} - {name} ({email})".format(guid=user.guid, name=user.name, email=user.email))


@manager.option("-a", "--agency", help="Create agency user.", action="store_true", dest='agency')
@manager.option("-g", "--google", help="Create google user.", action="store_true", dest='google')
@manager.option("-y", "--yahoo", help="Create yahoo user.", action="store_true", dest='yahoo')
@manager.option("-f", "--facebook", help="Create facebook user.", action="store_true", dest='facebook')
@manager.option("-l", "--linkedin", help="Create linkedin user.", action="store_true", dest='linkedin')
@manager.option("-m", "--microsoft", help="Create microsoft user.", action="store_true", dest='microsoft')
@manager.option("-e", "--edirsso", help="Create edirssoo user.", action="store_true", dest='edirsso')
def create_user(agency=False,
                google=False,
                yahoo=False,
                facebook=False,
                linkedin=False,
                microsoft=False,
                edirsso=False):
    """Create a user of the specified type. Defaults to an anonymous user."""
    from tests.lib.tools import create_user
    from app.constants.user_type_auth import (
        AGENCY_USER,
        PUBLIC_USER_NYC_ID,
        PUBLIC_USER_FACEBOOK,
        PUBLIC_USER_LINKEDIN,
        PUBLIC_USER_GOOGLE,
        PUBLIC_USER_YAHOO,
        PUBLIC_USER_MICROSOFT
    )
    if agency:
        user = create_user(AGENCY_USER)
    if edirsso:
        user = create_user(PUBLIC_USER_NYC_ID)
    if facebook:
        user = create_user(PUBLIC_USER_FACEBOOK)
    if linkedin:
        user = create_user(PUBLIC_USER_LINKEDIN)
    if google:
        user = create_user(PUBLIC_USER_GOOGLE)
    if yahoo:
        user = create_user(PUBLIC_USER_YAHOO)
    if microsoft:
        user = create_user(PUBLIC_USER_MICROSOFT)
    if not (facebook or google or linkedin or microsoft or yahoo or agency or edirsso):
        user = create_user()

    print(user, "created.")


@manager.command
def fix_anonymous_requesters():
    """
    Ensures there is only one anonymous requester per request by
    creating a new anonymous requester (User) for every User Requests record with
    a duplicate anonymous requester guid and updates the User Requests record.
    The new user will be identical to the existing one with the exception of the guid.
    """
    from app.constants import user_type_request, user_type_auth
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
    manager.run()
