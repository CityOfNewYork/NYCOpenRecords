# manage.py
import os
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from openrecords import create_app, db
from openrecords.models import User
from flask_script import Server, Manager

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
server = Server(host="0.0.0.0", port=8080)
manager.add_command("runserver", server)


migrate = Migrate(app, db)

def make_shell_context():
    return dict(app=app, db=db, User=User)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

@manager.command
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == "__main__":
    manager.run()


