from flask import url_for
from flask_login import login_user, logout_user
from unittest.mock import patch
from urllib.parse import urlparse

from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    RequestFactory,
    UserFactory,
    TestHelpers,
    login_user_with_client
)

from app.constants import request_status
from app.response.utils import add_closing


class ResponseViewsTests(BaseTestCase, TestHelpers):
    def setUp(self):
        super().setUp()
        self.agency_ein_860 = "0860"
        uf = UserFactory()
        self.agency_user_860 = uf.create_agency_user(agency_ein=self.agency_ein_860)
        self.admin_860 = uf.create_agency_admin(agency_ein=self.agency_ein_860)
        self.rf = RequestFactory
        self.rf_agency_860 = RequestFactory(agency_ein=self.agency_ein_860)
        self.request = self.rf_agency_860.create_request_as_public_user()

    def test_response_denial(self):
        with self.client as client:
            login_user_with_client(client, self.admin_860.get_id())
            response = self.client.post(
                '/response/denial/' + self.request.id,
                data={
                    "reasons": ['1', '2', '3'],
                    "email-summary": 'This is a email summary'
                }
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))

    def test_response_denial_missing_reasons(self):
        with self.client as client:
            login_user_with_client(client, self.admin_860.get_id())
            response = self.client.post(
                '/response/denial/' + self.request.id,
                data={
                    "email-summary": 'This is a email summary'
                }
            )
        self.assert_flashes(expected_message='Uh Oh, it looks like the denial reasons is missing! '
                                             'This is probably NOT your fault.', expected_category='danger')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))

    def test_response_closing(self):
        self.request.acknowledge(days=30)
        self.request.set_agency_description(agency_description='blah')
        self.request.set_agency_description_privacy(privacy=False)
        with self.client as client:
            login_user_with_client(client, self.admin_860.get_id())
            response = self.client.post(
                '/response/closing/' + self.request.id,
                data={
                    "reasons": ['1', '2', '3'],
                    "email-summary": 'This is a email summary'
                }
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))

    def test_response_closing_missing_reasons(self):
        self.request.acknowledge(days=30)
        with self.client as client:
            login_user_with_client(client, self.admin_860.get_id())
            response = self.client.post(
                '/response/closing/' + self.request.id,
                data={
                    "email-summary": 'This is a email summary'
                }
            )
        self.assert_flashes(expected_message='Uh Oh, it looks like the closing reasons is missing! '
                                             'This is probably NOT your fault.', expected_category='danger')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))

    def test_response_closing_no_agency_description(self):
        self.request.acknowledge(days=30)
        with self.client as client:
            login_user_with_client(client, self.admin_860.get_id())
            response = self.client.post(
                '/response/closing/' + self.request.id,
                data={
                    "reasons": ['1', '2', '3'],
                    "email-summary": 'This is a email summary'
                }
            )
        self.assert_flashes(expected_message='Unable to close request:', expected_category='danger')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))


class ResponseUtilsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.agency_ein_860 = "0860"
        uf = UserFactory()
        self.admin_860 = uf.create_agency_admin(agency_ein=self.agency_ein_860)
        self.rf = RequestFactory()
        self.rf_agency_860 = RequestFactory(agency_ein=self.agency_ein_860)
        self.request = self.rf_agency_860.create_request_as_public_user()

    def test_add_closing(self):
        login_user(self.admin_860)
        self.request.acknowledge(days=30)
        self.request.set_agency_description(agency_description='blah')
        self.request.set_agency_description_privacy(privacy=False)
        reasons = ['1', '2', '3']
        add_closing(self.request.id, reasons, 'email body')
        self.assertEqual(self.request.status, request_status.CLOSED)
        logout_user()