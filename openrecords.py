import os

from flask_migrate import Migrate

from app import create_app, db
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
    CustomRequestForms
)

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*',
                            config_file=os.path.join(os.curdir, '.coveragerc'))
    COV.start()

app = create_app(os.getenv('FLASK_CONFIG') or 'default', jobs_enabled=False)
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(app=app,
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
                CustomRequestForms=CustomRequestForms
                )


@app.cli.command()
@click.option('--coverage/--no-coverage', default=False, help='Run tests with coverage.py')
def test(coverage=False):
    """Test coverage"""
    if cov and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import pytest
    command = []

    if verbose:
        command.append('-v')

    if test_name:
        command.append('tests/{test_name}'.format(test_name=test_name))
    else:
        command.append('tests/')

    pytest.main(command)

    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        COV.html_report()
        COV.xml_report()


@app.cli.command()
@click.option('--length', default=25, help='Profile stack length')
@click.option('--profile-dir', default=None, help='Profile directory')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    # ...


@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # ...
