from app.models import (
    Agencies,
    Users
)
from manage import (
    create_user,
    import_data
)
from tests.lib.base import BaseTestCase
from tests.lib.constants import (
    USERS_CSV_FILE_PATH,
    AGENCIES_CSV_FILE_PATH
)
from flask_script.commands import InvalidCommand


class CreateUserTests(BaseTestCase):
    def test_called_create_user(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        create_user(first_name='John', last_name='Doe', email='bladerunnerperftest01@dsny.nyc.gov')
        self.assertEquals(Users.query.with_entities(Users.first_name, Users.last_name, Users.email).filter_by(
            email='bladerunnerperftest01@dsny.nyc.gov').first(), ('John', 'Doe', 'bladerunnerperftest01@dsny.nyc.gov'))

    def test_called_create_user_missing_first_name(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        with self.assertRaises(InvalidCommand):
            create_user(last_name='Doe', email='bladerunnerperftest01@dsny.nyc.gov')

    def test_called_create_user_missing_last_name(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        with self.assertRaises(InvalidCommand):
            create_user(first_name='John', email='bladerunnerperftest01@dsny.nyc.gov')

    def test_called_create_user_missing_first_name(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        with self.assertRaises(InvalidCommand):
            create_user(first_name='John', last_name='Doe')


class ImportDataTests(BaseTestCase):
    def test_called_import_users(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        import_data(users=True, agencies=False, filename=USERS_CSV_FILE_PATH)
        self.assertEquals(len(Users.query.all()), 1)

    def test_called_import_agencies(self):
        self.assertEquals(Agencies.query.filter_by(ein='9999').first(), None)
        import_data(users=False, agencies=True, filename=AGENCIES_CSV_FILE_PATH)
        self.assertEquals(len(Agencies.query.filter_by(ein='9999').all()), 1)

    def test_not_import_duplicate_agency(self):
        import_data(users=False, agencies=True, filename=AGENCIES_CSV_FILE_PATH)
        with self.assertWarns(UserWarning):
            import_data(users=False, agencies=True, filename=AGENCIES_CSV_FILE_PATH)
        self.assertEquals(len(Agencies.query.filter_by(ein='9999').all()), 1)
