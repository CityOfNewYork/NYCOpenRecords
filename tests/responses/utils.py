from random import choice
from sqlalchemy.orm.exc import NoResultFound
from unittest.mock import patch

from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    UserFactory,
    RequestFactory,
    TestHelpers,
    flask_login_user
)

from app.constants import (
    response_privacy,
    event_type,
    determination_type
)
from app.lib.utils import UserRequestException
from app.models import Determinations, Reasons
from app.response.utils import (
    add_denial,
    add_closing,
    format_determination_reasons
)


class ResponseUtilsTests(BaseTestCase, TestHelpers):
    def setUp(self):
        super().setUp()
        self.agency_ein_860 = "0860"
        uf = UserFactory()
        self.admin_860 = uf.create_agency_admin(agency_ein=self.agency_ein_860)
        self.rf = RequestFactory()
        self.rf_agency_860 = RequestFactory(agency_ein=self.agency_ein_860)
        self.request = self.rf_agency_860.create_request_as_public_user()
        self.email_content = 'test email body'
        self.closing_reasons = [choice([r.id for r in Reasons.query.filter_by(type=determination_type.CLOSING).all()])]
        self.denial_reasons = [choice([r.id for r in Reasons.query.filter_by(type=determination_type.DENIAL).all()])]

    @patch('app.response.utils._send_response_email')
    def test_add_denial(self, send_response_email_patch):
        with flask_login_user(self.admin_860):
            add_denial(self.request.id, self.denial_reasons, self.email_content)
            send_response_email_patch.assert_called_once_with(
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                self.email_content,
                'Request {} Closed'.format(self.request.id)
            )
        response = self.request.responses.join(Determinations).filter(
            Determinations.dtype == determination_type.DENIAL).one()
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.DENIAL,
                format_determination_reasons(self.denial_reasons)
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.admin_860)

    def test_add_denial_invalid_request(self):
        with flask_login_user(self.admin_860):
            with self.assertRaises(NoResultFound):
                add_denial('FOIL-2017-002-00001', self.denial_reasons, self.email_content)

    def test_add_denial_already_closed(self):
        with flask_login_user(self.admin_860):
            self.request.close()
            with self.assertRaises(UserRequestException):
                add_denial(self.request.id, self.denial_reasons, self.email_content)

    @patch('app.response.utils._send_response_email')
    def test_add_closing(self, send_response_email_patch):
        with flask_login_user(self.admin_860):
            self.request.acknowledge(days=30)
            self.request.set_agency_request_summary('blah')
            self.request.set_agency_request_summary_privacy(False)
            add_closing(self.request.id, self.closing_reasons, self.email_content)
            send_response_email_patch.assert_called_once_with(
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                self.email_content,
                'Request {} Closed'.format(self.request.id)
            )
        response = self.request.responses.join(Determinations).filter(
            Determinations.dtype == determination_type.CLOSING).one()
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(self.closing_reasons)
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.admin_860)

    def test_add_closing_invalid_request(self):
        with flask_login_user(self.admin_860):
            with self.assertRaises(NoResultFound):
                add_closing('FOIL-2017-002-00001', self.closing_reasons, self.email_content)

    def test_add_closing_not_acknowledged(self):
        with flask_login_user(self.admin_860):
            self.request.close()
            with self.assertRaises(UserRequestException):
                add_closing(self.request.id, self.closing_reasons, self.email_content)

    def test_add_closing_already_closed(self):
        with flask_login_user(self.admin_860):
            self.request.close()
            with self.assertRaises(UserRequestException):
                add_closing(self.request.id, self.closing_reasons, self.email_content)

    def test_add_closing_no_agency_request_summary(self):
        with flask_login_user(self.admin_860):
            self.request.acknowledge(days=30)
            with self.assertRaises(UserRequestException):
                add_closing(self.request.id, self.closing_reasons, self.email_content)

    def test_add_closing_file_private(self):
        with flask_login_user(self.admin_860):
            self.request.acknowledge(days=30)
            self.request.add_file()
            with self.assertRaises(UserRequestException):
                add_closing(self.request.id, self.closing_reasons, self.email_content)

    @patch('app.response.utils._send_response_email')
    def test_add_closing_file_release_public(self, send_response_email_patch):
        request_title_public = self.rf_agency_860.create_request_as_public_user(title_privacy=False)
        with flask_login_user(self.admin_860):
            request_title_public.acknowledge(days=30)
            request_title_public.add_file(privacy=response_privacy.RELEASE_AND_PUBLIC)
            add_closing(request_title_public.id, self.closing_reasons, self.email_content)
            send_response_email_patch.assert_called_once_with(
                request_title_public.id,
                response_privacy.RELEASE_AND_PUBLIC,
                self.email_content,
                'Request {} Closed'.format(request_title_public.id)
            )
        response = request_title_public.responses.join(Determinations).filter(
            Determinations.dtype == determination_type.CLOSING).one()
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                request_title_public.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(self.closing_reasons)
            ]
        )
        self.assert_response_event(request_title_public.id, event_type.REQ_CLOSED, response, self.admin_860)

    @patch('app.response.utils._send_response_email')
    def test_add_closing_not_fulfilled_reasons(self, send_response_email_patch):
        not_fulfilled_reasons = ['7', '8', '9']
        with flask_login_user(self.admin_860):
            self.request.acknowledge(days=30)
            self.request.set_agency_request_summary('blah')
            self.request.set_agency_request_summary_privacy(False)
            add_closing(self.request.id, not_fulfilled_reasons, self.email_content)
            send_response_email_patch.assert_called_once_with(
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                self.email_content,
                'Request {} Closed'.format(self.request.id)
            )
        response = self.request.responses.join(Determinations).filter(
            Determinations.dtype == determination_type.CLOSING).one()
        self.assertEqual(
            [
                response.request_id,
                response.privacy,
                response.dtype,
                response.reason
            ],
            [
                self.request.id,
                response_privacy.RELEASE_AND_PUBLIC,
                determination_type.CLOSING,
                format_determination_reasons(not_fulfilled_reasons)
            ]
        )
        self.assert_response_event(self.request.id, event_type.REQ_CLOSED, response, self.admin_860)
