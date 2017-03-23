import os
from tests.lib.base import BaseTestCase
from manage import (
    import_data
)
from app.models import (
    Users,
    Agencies
)
from tests.lib.constants import (
    USERS_CSV_FILE_PATH,
    AGENCIES_CSV_FILE_PATH
)


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
