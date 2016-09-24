# manage.py
import os

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db
from app.models import User, Agency, Request, Response, Event, Reason, Permission, Role

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(
        app=app,
        db=db,
        User=User,
        Agency=Agency,
        Request=Request,
        Response=Response,
        Event=Event,
        Reason=Reason,
        Permission=Permission,
        Role=Role
    )

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
if __name__ == "__main__":
    manager.run()
