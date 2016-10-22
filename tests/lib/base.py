import unittest
from app import create_app, db
from app.models import Roles, Agencies


class BaseTestCase(unittest.TestCase):

    app = create_app('testing')

    @classmethod
    def setUpClass(cls):
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.populate_database()

    def tearDown(self):
        self.clear_database()
        self.app_context.pop()

    @staticmethod
    def clear_database():
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

    @staticmethod
    def populate_database():
        Roles.populate()
        Agencies.populate()
