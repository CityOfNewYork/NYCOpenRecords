# manage.py
import os
import subprocess

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db
from app.models import Users, Agencies, Requests, Responses, Events, Reasons, Permissions, Roles

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
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
        Permissions=Permissions,
        Roles=Roles
    )

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

@manager
def celery():
    subprocess.call(['celery', 'worker',  '-A', 'celery_worker.celery', '--loglevel=info'])


if __name__ == "__main__":
    manager.run()
