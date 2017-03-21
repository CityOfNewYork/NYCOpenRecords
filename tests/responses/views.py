from unittest.mock import patch

from tests.lib.base import BaseTestCase
from tests.lib.tools import RequestFactory, UserFactory


class ResponseViewsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.agency_ein_860 = "0860"
        uf = UserFactory()
        self.admin_860 = uf.create_agency_admin(agency_ein=self.agency_ein_860)
        self.rf = RequestFactory
        self.rf_agency_860 = RequestFactory(agency_ein=self.agency_ein_860)

    def test_response_closing(self):
        request = self.rf_agency_860.create_request_as_public_user()
        request.acknowledge(days=30)
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = self.admin_860.get_id()
                session['_fresh'] = True
            response = self.client.post(
                '/response/closing/' + request.id,
                data={
                    "reasons": ['1', '2', '3'],
                    "email-summary": 'This is a email summary'
                }
            )