"""
    `.`  `.`         ...`       ....         ...`
  `;'',  :##+   +##`#####,    .######`  +##.+####'
 `'''',  :####  +#########,  .########` '#########,
 ;'';`    `###' +###,``;###``###. `;##+ '###,``####
.'''`      `### +##'    ###,:##:    ###`'##+   .###
.'''        ###.+##,    :##'###+++++###.'##,   `###
.:::,,,     ###.+##`    ,##+###########.'##:   `###
   .###     ###.+##.    :##+###,.......`'##:   `###
   `###`   `### +##;    +##:;##,    ...`'##:   `###
    +##+   ###+ +###.  .###.`###.  .### '##:   `###
    `#########` +#########'  ;########. '##:   `###
     `#######`  +##,#####'    ,######.  '##:   `###
       `,:,`    +##, .:,`      `.::.    ````    ```
                +##,
                +##,
                +##,
                ```

    .........`     ............`     .,::,.          ,,;:,`      ..........     `........          .,::,.
   `'''''''''''.   ''''''''''''.   .''''''''`      ,''''''''.    ;'''''''''':   .''''''''''.     `'''''''',
   `''''''''''''.  ''''''''''''.  ,''''''''''.    ;''''''''''`   ;''''''''''''  .''''''''''':   `'''''''''',
   `''':::::;''''  '''';;;;;;;;. .'''':.,:''''`  :'''',.,:''''.  ;'''::::,''''. .''';;;;''''',  ;'''.``.''''`
   `'''.     ,'''` ''''          ''''`    `''': `''''     .''''  ;'''     .''': .'''`    ,''''` ''',    `'''.
   `'''.     .'''. ''''         ,'''.      :''' :'''`      ,'''. ;'''      '''; .'''`     ,''', ''',     :,:.
   `'''.     .'''` ''''         ;'''       ```` ''';       .''', ;'''      ''', .'''`      '''; '''';.
   `'''.    `''''  ''''''''''': ''';           `''',        ''': ;'''     ,'''` .'''`      ;''' .''''''':.
   `''''''''''''   ''''''''''': ''':           `'''.        '''; ;'''''''''''.  .'''`      :'''  .'''''''''.
   `'''''''''''.   '''''''''''; ''':           `'''.        '''; ;'''''''''':   .'''`      ;'''    ,''''''''.
   `''':::::''''.  ''''         ''''       `...`''':        ''': ;'''::::;''''  .'''`      ;'''       .,'''''
   `'''.     ''''  ''''         :'''`      :''' ''''       .'''. ;'''     ,'''` .'''`      ''':,:::      ;'''`
   `'''.     ,'''  ''';         .''':      '''' ,'''.      ;'''` ;'''      ''', .'''`     :'''.:'''      .'''`
   `'''.     .'''  ''''          '''',    :'''.  ''''.    :''':  ;'''      ''', .'''.   .;'''' .''':     ;'''
   `'''.     `'''` '''''''''''', `''''';;'''''   .''''';''''''   ;'''      ''', .''''''''''''.  ''''':::'''',
   `'''.      '''. ''''''''''''.  .''''''''''     .''''''''''`   ;'''      ;''; .'''''''''''.    '''''''''';
   `'''.      ''': '''''''''''',    ,'''''',       `:''''''.     ''''      ,''' .'''''''';.       ,'''''''.

"""

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)

from datetime import datetime
from urllib.parse import unquote, urljoin
import sys
import traceback
import click

from flask import url_for, render_template, request as flask_request
from flask.cli import main
from flask_login import login_user
from flask_migrate import Migrate, upgrade
from werkzeug.contrib.profiler import ProfilerMiddleware

from app import create_app, db
from app.constants import OPENRECORDS_DL_EMAIL, request_status
from app.jobs import _update_request_statuses
from app.lib.date_utils import process_due_date, local_to_utc
from app.lib.email_utils import send_email
from app.models import (
    Agencies,
    AgencyUsers,
    CustomRequestForms,
    Determinations,
    Emails,
    EnvelopeTemplates,
    Envelopes,
    Events,
    LetterTemplates,
    Letters,
    Reasons,
    Requests,
    Responses,
    Roles,
    UserRequests,
    Users,
)
from app.report.utils import generate_request_closing_user_report, generate_monthly_metrics_report
from app.request.utils import generate_guid
from app.response.utils import add_extension, add_closing_cli
from app.search.utils import recreate
from app.user.utils import make_user_admin

if os.getenv('FLASK_ENV') != 'production':
    import pytest

app = create_app(os.getenv("FLASK_CONFIG") or "default")

migrate = Migrate(app, db)

COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage

    COV = coverage.coverage(
        branch=True, include="app/*", config_file=os.path.join(os.curdir, ".coveragerc")
    )
    COV.start()


@app.shell_context_processor
def make_shell_context():
    return dict(
        app=app,
        db=db,
        Users=Users,
        Agencies=Agencies,
        Determinations=Determinations,
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


@app.cli.command()
@click.option("--first_name", prompt="First Name")
@click.option("--middle_initial", default="", prompt="Middle Initial")
@click.option("--last_name", prompt="Last Name")
@click.option("--email", prompt="Email Address")
@click.option("--agency_ein", prompt="Agency EIN (e.g. 0002)")
@click.option(
    "--is_admin", default=False, prompt="Should user be made an agency administrator?"
)
@click.option(
    "--is_active", default=False, prompt="Should user be activated immediately?"
)
def add_user(
        first_name: str,
        last_name: str,
        email: str,
        agency_ein: str,
        middle_initial: str = None,
        is_admin: bool = False,
        is_active: bool = False,
):
    """
    Add an agency user into the database.
    """
    if not first_name:
        raise click.UsageError("First name is required")
    if not last_name:
        raise click.UsageError("Last name is required")
    if not email:
        raise click.UsageError("Email Address is required")
    if not agency_ein:
        raise click.UsageError("Agency EIN is required")

    user = Users(
        guid=generate_guid(),
        first_name=first_name,
        middle_initial=middle_initial,
        last_name=last_name,
        email=email,
        email_validated=False,
        is_nyc_employee=True,
        is_anonymous_requester=False,
    )
    db.session.add(user)

    agency_user = AgencyUsers(
        user_guid=user.guid,
        agency_ein=agency_ein,
        is_agency_active=is_active,
        is_agency_admin=is_admin,
        is_primary_agency=True,
    )

    db.session.add(agency_user)
    db.session.commit()
    if is_admin:
        redis_key = "{current_user_guid}-{update_user_guid}-{agency_ein}-{timestamp}".format(
            current_user_guid="openrecords_support",
            update_user_guid=user.guid,
            agency_ein=agency_ein,
            timestamp=datetime.now(),
        )
        make_user_admin.apply_async(
            args=(user.guid, "openrecords_support", agency_ein), task_id=redis_key
        )

    print(user)


@app.cli.command()
@click.option("--agency_ein", prompt="Agency EIN (e.g. 0002)")
@click.option("--date_from", prompt="Date From (e.g. 2000-01-01")
@click.option("--date_to", prompt="Date To (e.g. 2000-02-01)")
@click.option("--emails", prompt="Emails (e.g. test@mailinator.com,test2@mailinator.com)")
def generate_closing_report(agency_ein: str, date_from: str, date_to: str, emails: str):
    """Generate request closing report.
    """
    email_list = emails.split(',')
    generate_request_closing_user_report(agency_ein, date_from, date_to, email_list)


@app.cli.command()
@click.option("--agency_ein", prompt="Agency EIN (e.g. 0002)")
@click.option("--date_from", prompt="Date From (e.g. 2000-01-01")
@click.option("--date_to", prompt="Date To (e.g. 2000-02-01)")
@click.option("--emails", prompt="Emails (e.g. test@mailinator.com,test2@mailinator.com)")
def generate_monthly_report(agency_ein: str, date_from: str, date_to: str, emails: str):
    """Generate monthly metrics report.

    CLI command to generate monthly metrics report.
    Purposely leaving a full date range option instead of a monthly limit in order to provide more granularity for devs.
    """
    email_list = emails.split(',')
    generate_monthly_metrics_report(agency_ein, date_from, date_to, email_list)


@app.cli.command()
def es_recreate():
    """
    Recreate elasticsearch index and request docs.
    """
    recreate()


@app.cli.command()
@click.option("--agency_ein", prompt="Agency EIN (e.g. 0056)")
@click.option("--agency_name", prompt="Agency Name (e.g. New York City Police Department (NYPD))")
@click.option("--user_guid", prompt="User GUID")
@click.option("--extension_date", prompt="Extension Date (e.g. 01/01/2022)")
@click.option("--extension_reason", prompt="Extension Reason")
def extend_requests(agency_ein: str, agency_name: str, user_guid: str, extension_date: str, extension_reason: str):
    # Create request context
    ctx = app.test_request_context()
    ctx.push()
    app.preprocess_request()

    # Select user to perform the extensions
    user = Users.query.filter_by(guid=user_guid).first()
    login_user(user)

    # Extend overdue requests
    overdue_requests = Requests.query.filter_by(agency_ein=agency_ein, status='Overdue').order_by(Requests.id).all()
    for request in overdue_requests:
        try:
            date = datetime.strptime(extension_date, '%m/%d/%Y')
            new_due_date = process_due_date(local_to_utc(date, 'America/New_York'))
            email_template = render_template('email_templates/email_response_extension_cli.html',
                                   default_content=True,
                                   content=None,
                                   request=request,
                                   request_id=request.id,
                                   agency_name=agency_name,
                                   new_due_date=new_due_date.strftime("%A, %B %-d, %Y"),
                                   reason=extension_reason,
                                   page=urljoin(app.config['BASE_URL'], url_for('request.view', request_id=request.id)))
            add_extension(request.id,
                          '-1',
                          extension_reason,
                          extension_date,
                          'America/New_York',
                          email_template,
                          'emails',
                          '')
            print(request.id, 'extended')
        except:
            print(request.id, 'failed')


@app.cli.command()
@click.option("--agency_ein", prompt="Agency EIN (e.g. 0056)")
@click.option("--user_guid", prompt="User GUID")
@click.option("--reason_text", prompt="Reason text")
@click.option("--requests_to_close_file", prompt="Requests to close file", default="")
def close_requests(agency_ein: str, user_guid: str, reason_text: str, requests_to_close_file: str):
    # Create request context
    ctx = app.test_request_context()
    ctx.push()
    app.preprocess_request()

    # Select user to perform the extensions
    user = Users.query.filter_by(guid=user_guid).first()
    login_user(user)

    # Close open requests
    if requests_to_close_file:
        file = open(requests_to_close_file)
        data = file.read()
        data_to_list = data.split("\n")
        open_requests = Requests.query.filter(Requests.agency_ein==agency_ein, Requests.status!=request_status.CLOSED, Requests.id.in_(data_to_list)).order_by(Requests.id).all()
    else:
        open_requests = Requests.query.filter(Requests.agency_ein==agency_ein, Requests.status!=request_status.CLOSED).order_by(Requests.id).all()
    for request in open_requests:
        try:
            # Close request
            add_closing_cli(
                request.id,
                reason_text,
            )
            print(request.id, 'closed')
        except Exception as e:
            print(request.id, 'failed')
            print(e)


@app.cli.command()
def update_request_statuses():
    _update_request_statuses()


@app.cli.command
def routes():
    """
    Generate a list of HTTP routes for the application.
    """

    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            if arg == "year":
                options[arg] = "{}".format(datetime.now().year)
                continue
            options[arg] = "[{}]".format(arg)

        methods = ",".join(rule.methods)
        url = url_for(rule.endpoint, **options)

        if str(datetime.now().year) in url:
            url = url.replace(str(datetime.now().year), "[year]")
        line = unquote("{:50} {:20} {}".format(rule.endpoint, methods, url))

        output.append(line)

    for line in sorted(output):
        print(line)


@app.cli.command()
@click.option("--test-name", help="Specify tests (file, class, or specific test)")
@click.option(
    "--coverage/--no-coverage", "use_coverage", default=False, help="Run tests under code coverage."
)
@click.option("--verbose", is_flag=True, default=False, help="Py.Test verbose mode")
def test(test_name: str = None, use_coverage: bool = False, verbose: bool = False):
    """Run the unit tests."""

    if use_coverage and not os.environ.get("FLASK_COVERAGE"):
        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable] + sys.argv)

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


@app.cli.command()
@click.option(
    "--length",
    default=25,
    help="Number of functions to include in the profiler report.",
)
@click.option(
    "--profile-dir", default=None, help="Directory where profiler data files are saved."
)
def profile(length, profile_dir):
    """
    Start the application under the code profiler.
    """

    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app, restrictions=[length], profile_dir=profile_dir
    )
    app.run()


@app.cli.command()
def deploy():
    """
    Run deployment tasks.
    """

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
    recreate()


if __name__ == "__main__":
    main()
