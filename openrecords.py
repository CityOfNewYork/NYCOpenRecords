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

from datetime import datetime

import click
import os
import pytest
from flask.cli import main
from flask_migrate import Migrate

from app import create_app, db
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
from app.request.utils import generate_guid
from app.user.utils import make_user_admin

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
        guid=generate_guid,
        email=email,
        first_name=first_name,
        middle_initial=middle_initial,
        last_name=last_name,
        is_nyc_employee=True,
    )
    db.session.add(user)

    agency_user = AgencyUsers(
        user_guid=user.guid,
        agency_ein=ein,
        is_agency_active=is_active,
        is_agency_admin=is_admin,
        is_primary_agency=True,
    )

    db.session.add(agency_user)
    db.session.commit()
    if is_admin:
        redis_key = "{current_user_guid}-{update_user_guid}-{agency_ein}-{timestamp}".format(
            current_user_guid="openrecords_support",
            pdate_user_guid=user.guid,
            agency_ein=ein,
            timestamp=datetime.now(),
        )
        make_user_admin.apply_async(
            args=(user.guid, "openrecords_support", ein), task_id=redis_key
        )

    print(user)


@app.cli.command
def es_recreate():
    """
    Recreate elasticsearch index and request docs.
    """
    from app.search.utils import recreate

    recreate()


@app.cli.command
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


@app.cli.command()
@click.option("--test-name", help="Specify tests (file, class, or specific test)")
@click.option(
    "--coverage/--no-coverage", default=False, help="Run tests under code coverage."
)
@click.option("--verbose", is_flag=True, default=False, help="Py.Test verbose mode")
def test(test_name: str = None, coverage: bool = False, verbose: bool = False):
    """Run the unit tests."""

    if coverage and not os.environ.get("FLASK_COVERAGE"):
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
    from werkzeug.contrib.profiler import ProfilerMiddleware

    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app, restrictions=[length], profile_dir=profile_dir
    )
    app.run()


@app.cli.command()
def deploy():
    """
    Run deployment tasks.
    """
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


if __name__ == "__main__":
    main()
