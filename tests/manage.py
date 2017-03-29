import os
from psycopg2 import ProgrammingError
from tests.lib.base import BaseTestCase
from manage import (
    create_user,
    import_data,
    deploy
)
from app.models import (
    Agencies,
    Determinations,
    Emails,
    Events,
    Files,
    Instructions,
    Links,
    Notes,
    Reasons,
    Requests,
    ResponseTokens,
    Responses,
    Roles,
    UserRequests,
    Users
)
from tests.lib.constants import (
    USERS_CSV_FILE_PATH,
    AGENCIES_CSV_FILE_PATH
)


class CreateUserTests(BaseTestCase):
    def test_called_create_user(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        create_user(first_name='John', last_name='Doe', email='bladerunnerperftest01@dsny.nyc.gov')
        self.assertEquals(Users.query.with_entities(Users.first_name, Users.last_name, Users.email).filter_by(
            email='bladerunnerperftest01@dsny.nyc.gov').first(), ('John', 'Doe', 'bladerunnerperftest01@dsny.nyc.gov'))


class DeployTests(BaseTestCase):
    @classmethod
    def setUpClass(cls, create_db=False, create_es_index=True):
        super().setUpClass(create_db=create_db, create_es_index=create_es_index)

    def setUp(self, populate=False):
        super().setUp(populate=populate)

    def test_called_upgrade(self):
        import ipdb; ipdb.set_trace()
        try:
            Users.query.all()
        except Exception as e:
            print(type(e))
        # self.assertRaises(ProgrammingError, Users.query.all())
        # deploy()
        # Users.query.all()
        self.assert_(True)


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
