# manage.py
import sys
import os
from datetime import timedelta

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask_script.commands import InvalidCommand

from app import create_app, db, sentry
from app.models import (
    Users,
    Agencies,
    Requests,
    Responses,
    Events,
    Reasons,
    Roles,
    UserRequests,
    AgencyUsers,
    Emails,
    Letters,
    LetterTemplates,
    Envelopes,
    EnvelopeTemplates,
    CustomRequestForms,
    Determinations,
)
from app.request.utils import generate_guid
from app.constants import user_type_auth, event_type, determination_type
from app.lib.user_information import create_mailing_address

COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage

    COV = coverage.coverage(
        branch=True, include="app/*", config_file=os.path.join(os.curdir, ".coveragerc")
    )
    COV.start()

app = create_app(os.getenv("FLASK_CONFIG") or "default", jobs_enabled=False)
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
        Agencies.populate(csv_name=filename)


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
        import sys

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
    from app.models import Roles, Agencies, Reasons

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
def create_missing_request_status_changed_events():
    """
    http://nycrecords.atlassian.net/browse/OP-1532
    """
    from app.constants import request_status
    from datetime import datetime

    release_date = datetime(2018, 8, 30, 17, 00)
    events = Events.query.filter(
        Events.type.in_([event_type.REQ_CLOSED]), Events.timestamp >= release_date
    ).all()

    requests = [Requests.query.filter_by(id=e.request_id).one() for e in events]

    for request in requests:
        # Get the time for the "request_closed" event
        request_closed_date = Events.query.filter_by(
            request_id=request.id, type=event_type.REQ_CLOSED
        ).all()
        if len(request_closed_date) == 1:
            request_closed_event = request_closed_date[0]

            # Determine if the request was "Due Soon" or "Overdue" at some point
            has_request_status_changed = Events.query.filter(
                Events.type == event_type.REQ_STATUS_CHANGED,
                Events.request_id == request.id,
            ).all()
            if has_request_status_changed:
                # Get the last request_status_changed event from the database
                has_request_status_changed.sort(key=lambda x: x.timestamp, reverse=True)
                last_status = has_request_status_changed[0]
            else:
                last_status = []

            if last_status:
                # This request was "Due Soon" or "Overdue"; We'll use the last status (from the request_status_changed
                # new_value) to insert the request_status_changed event for this into the DB
                event = Events(
                    request_id=request.id,
                    user_guid=request_closed_event.user_guid,
                    auth_user_type=request_closed_event.auth_user_type,
                    type_=event_type.REQ_STATUS_CHANGED,
                    previous_value={
                        "status": last_status.new_value["status"],
                        "date_closed": None,
                    },
                    new_value={
                        "status": request_status.CLOSED,
                        "date_closed": request_closed_event.timestamp.isoformat(),
                    },
                    timestamp=request_closed_event.timestamp
                    - timedelta(microseconds=30),
                )
                print(
                    request.id,
                    request.date_closed,
                    event.timestamp,
                    event.previous_value,
                    event.new_value,
                )

                db.session.add(event)
            else:
                # Determine if the previous status was "In Progress" (the request was previously acknowledged, or
                # "Open" (the request was denied outright)
                was_acknowledged = (
                    request.responses.join(Determinations)
                    .filter(Determinations.dtype == determination_type.ACKNOWLEDGMENT)
                    .one_or_none()
                )
                if was_acknowledged:
                    # The request was acknowledged, so the previous status has to be "In Progress"
                    event = Events(
                        request_id=request.id,
                        user_guid=request_closed_event.user_guid,
                        auth_user_type=request_closed_event.auth_user_type,
                        type_=event_type.REQ_STATUS_CHANGED,
                        previous_value={
                            "status": request_status.IN_PROGRESS,
                            "date_closed": None,
                        },
                        new_value={
                            "status": request_status.CLOSED,
                            "date_closed": request_closed_event.timestamp.isoformat(),
                        },
                        timestamp=request_closed_event.timestamp
                        - timedelta(microseconds=30),
                    )
                    print(
                        request.id,
                        request.date_closed,
                        event.timestamp,
                        event.previous_value,
                        event.new_value,
                    )

                    db.session.add(event)
                else:
                    # The request was not acnkowledged, so the previous status has to be "Open"
                    event = Events(
                        request_id=request.id,
                        user_guid=request_closed_event.user_guid,
                        auth_user_type=request_closed_event.auth_user_type,
                        type_=event_type.REQ_STATUS_CHANGED,
                        previous_value={
                            "status": request_status.OPEN,
                            "date_closed": None,
                        },
                        new_value={
                            "status": request_status.CLOSED,
                            "date_closed": request_closed_event.timestamp.isoformat(),
                        },
                        timestamp=request_closed_event.timestamp
                        - timedelta(microseconds=30),
                    )
                    print(
                        request.id,
                        request.date_closed,
                        event.timestamp,
                        event.previous_value,
                        event.new_value,
                    )

                    db.session.add(event)
        else:
            # Handle requests that were closed multiple times
            request_closed_date.sort(key=lambda x: x.timestamp, reverse=True)
            for closing in request_closed_date[:-1]:
                # The last request has to be handled differently.
                next_closing = request_closed_date.index(closing) + 1
                # Find all request status changes that happened in between the current closing and the previous closing.
                has_request_status_changed = Events.query.filter(
                    Events.type == event_type.REQ_STATUS_CHANGED,
                    Events.request_id == request.id,
                    Events.timestamp < closing.timestamp,
                    Events.timestamp >= request_closed_date[next_closing].timestamp,
                ).all()

                if has_request_status_changed:
                    # Get the last request_status_changed event from the database
                    has_request_status_changed.sort(
                        key=lambda x: x.timestamp, reverse=True
                    )
                    last_status = has_request_status_changed[0]
                else:
                    last_status = []

                if last_status:
                    # This request was "Due Soon" or "Overdue"; We'll use the last status (from the request_status
                    # _changed new_value) to insert the request_status_changed event for this into the DB
                    event = Events(
                        request_id=request.id,
                        user_guid=closing.user_guid,
                        auth_user_type=closing.auth_user_type,
                        type_=event_type.REQ_STATUS_CHANGED,
                        previous_value={
                            "status": last_status.new_value["status"],
                            "date_closed": None,
                        },
                        new_value={
                            "status": request_status.CLOSED,
                            "date_closed": closing.timestamp.isoformat(),
                        },
                        timestamp=closing.timestamp - timedelta(microseconds=30),
                    )
                    print(
                        request.id,
                        closing.timestamp,
                        event.timestamp,
                        event.previous_value,
                        event.new_value,
                    )
                    db.session.add(event)
                else:
                    # Determine if the previous status was "In Progress" (the request was previously acknowledged, or
                    # "Open" (the request was denied outright)
                    was_acknowledged = (
                        request.responses.join(Determinations)
                        .filter(
                            Determinations.dtype == determination_type.ACKNOWLEDGMENT
                        )
                        .one_or_none()
                    )
                    if was_acknowledged:
                        # The request was acknowledged, so the previous status has to be "In Progress"
                        event = Events(
                            request_id=request.id,
                            user_guid=closing.user_guid,
                            auth_user_type=closing.auth_user_type,
                            type_=event_type.REQ_STATUS_CHANGED,
                            previous_value={
                                "status": request_status.IN_PROGRESS,
                                "date_closed": None,
                            },
                            new_value={
                                "status": request_status.CLOSED,
                                "date_closed": closing.timestamp.isoformat(),
                            },
                            timestamp=closing.timestamp - timedelta(microseconds=30),
                        )
                        print(
                            request.id,
                            closing.timestamp,
                            event.timestamp,
                            event.previous_value,
                            event.new_value,
                        )

                        db.session.add(event)
                    else:
                        # The request was not acnkowledged, so the previous status has to be "Open"
                        event = Events(
                            request_id=request.id,
                            user_guid=closing.user_guid,
                            auth_user_type=closing.auth_user_type,
                            type_=event_type.REQ_STATUS_CHANGED,
                            previous_value={
                                "status": request_status.OPEN,
                                "date_closed": None,
                            },
                            new_value={
                                "status": request_status.CLOSED,
                                "date_closed": closing.timestamp.isoformat(),
                            },
                            timestamp=closing.timestamp - timedelta(microseconds=30),
                        )
                        print(
                            request.id,
                            closing.timestamp,
                            event.timestamp,
                            event.previous_value,
                            event.new_value,
                        )

                        db.session.add(event)
            closing = request_closed_date[-1]
            has_request_status_changed = Events.query.filter(
                Events.type == event_type.REQ_STATUS_CHANGED,
                Events.request_id == request.id,
                Events.timestamp < closing.timestamp,
            ).all()

            if has_request_status_changed:
                # Get the last request_status_changed event from the database
                has_request_status_changed.sort(key=lambda x: x.timestamp, reverse=True)
                last_status = has_request_status_changed[0]
            else:
                last_status = []

            if last_status:
                # This request was "Due Soon" or "Overdue"; We'll use the last status (from the request_status
                # _changed new_value) to insert the request_status_changed event for this into the DB
                event = Events(
                    request_id=request.id,
                    user_guid=closing.user_guid,
                    auth_user_type=closing.auth_user_type,
                    type_=event_type.REQ_STATUS_CHANGED,
                    previous_value={
                        "status": last_status.new_value["status"],
                        "date_closed": None,
                    },
                    new_value={
                        "status": request_status.CLOSED,
                        "date_closed": closing.timestamp.isoformat(),
                    },
                    timestamp=closing.timestamp - timedelta(microseconds=30),
                )
                print(
                    request.id,
                    closing.timestamp,
                    event.timestamp,
                    event.previous_value,
                    event.new_value,
                )
                db.session.add(event)
            else:
                # Determine if the previous status was "In Progress" (the request was previously acknowledged, or
                # "Open" (the request was denied outright)
                was_acknowledged = (
                    request.responses.join(Determinations)
                    .filter(Determinations.dtype == determination_type.ACKNOWLEDGMENT)
                    .one_or_none()
                )
                if was_acknowledged:
                    # The request was acknowledged, so the previous status has to be "In Progress"
                    event = Events(
                        request_id=request.id,
                        user_guid=closing.user_guid,
                        auth_user_type=closing.auth_user_type,
                        type_=event_type.REQ_STATUS_CHANGED,
                        previous_value={
                            "status": request_status.IN_PROGRESS,
                            "date_closed": None,
                        },
                        new_value={
                            "status": request_status.CLOSED,
                            "date_closed": closing.timestamp.isoformat(),
                        },
                        timestamp=closing.timestamp - timedelta(microseconds=30),
                    )
                    print(
                        request.id,
                        closing.timestamp,
                        event.timestamp,
                        event.previous_value,
                        event.new_value,
                    )
                    db.session.add(event)
                else:
                    # The request was not acknowledge, so the previous status has to be "Open"
                    event = Events(
                        request_id=request.id,
                        user_guid=closing.user_guid,
                        auth_user_type=closing.auth_user_type,
                        type_=event_type.REQ_STATUS_CHANGED,
                        previous_value={
                            "status": request_status.OPEN,
                            "date_closed": None,
                        },
                        new_value={
                            "status": request_status.CLOSED,
                            "date_closed": closing.timestamp.isoformat(),
                        },
                        timestamp=closing.timestamp - timedelta(microseconds=30),
                    )
                    print(
                        request.id,
                        closing.timestamp,
                        event.timestamp,
                        event.previous_value,
                        event.new_value,
                    )
                    db.session.add(event)
    db.session.commit()

@manager.command
def fix_incorrect_key_events():
    """
    Fixes Events table for request_status_changed events with a key of 'request' instead of 'status'
    """
    from sqlalchemy.orm.attributes import flag_modified

    events = Events.query.filter(Events.type == "request_status_changed").all()

    for event in events:
        if "request" in event.previous_value:
            print(event.request_id)
            event.previous_value["status"] = event.previous_value["request"]
            event.previous_value.pop("request", None)
            db.session.add(event)
            flag_modified(event, "previous_value")

    db.session.commit()


if __name__ == "__main__":
    try:
        manager.run()
    except InvalidCommand as err:
        sentry.captureException()
        print(err, file=sys.stderr)
        sys.exit(1)
