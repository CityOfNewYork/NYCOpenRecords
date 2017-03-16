import os
from tests.lib.base import BaseTestCase
from manage import (
    import_data
)
from app.models import (
    Users,
    Agencies
)


class ImportDataTests(BaseTestCase):
    def test_called_import_users(self):
        self.assertEquals(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').first(), None)
        import_data(users=True, filename=os.path.join(os.getcwd(), 'fixtures/data/test_users.csv'))
        self.assertEquals(len(Users.query.filter_by(email='bladerunnerperftest01@dsny.nyc.gov').all()), 1)
