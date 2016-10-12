# manage.py
import os
import subprocess

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell, Command

from app import create_app, db
from app.models import Users, Agencies, Requests, Responses, Events, Reasons, Roles

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


class Celery(Command):
    """
    Runs Celery
    """

    # TODO: autoreload and background options?
    # http://stackoverflow.com/questions/21666229/celery-auto-reload-on-any-changes
    # http://docs.celeryproject.org/en/latest/tutorials/daemonizing.html

    def run(self):
        subprocess.call(['celery', 'worker', '-A', 'celery_worker.celery', '--loglevel=info'])


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
        Roles=Roles
    )


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)
manager.add_command("celery", Celery())


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests', pattern='*.py')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


if __name__ == "__main__":
    manager.run()
