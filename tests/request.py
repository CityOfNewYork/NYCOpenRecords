from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from flask import (
    jsonify,
    url_for
)
from unittest.mock import patch
from urllib.parse import urlparse

from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    TestHelpers,
    UserFactory,
    RequestFactory,
    flask_login_user,
    login_user_with_client,
)

from app.models import (
    Users,
    Events,
    Emails
)
from app.constants import (
    user_type_auth,
    event_type
)
from app.request.utils import create_contact_record
from app.lib.email_utils import get_agency_emails
from app.lib.date_utils import get_holidays_date_list, DEFAULT_YEARS_HOLIDAY_LIST


class RequestViewsTests(BaseTestCase, TestHelpers):
    def setUp(self):
        super().setUp()
        uf = UserFactory()
        self.agency_admin = uf.create_agency_admin()
        self.request = RequestFactory().create_request_as_anonymous_user()

    @patch('app.request.views.SearchRequestsForm')
    @patch('app.request.views.render_template', return_value=jsonify({}))  # FIXME: return_value
    def test_view_all_agency(self, render_template_patch, search_requests_form_patch):
        """
        Test render_template in request.views.view_all is called once for logged in agency user.
        """
        # login agency_user
        with self.client as client:
            login_user_with_client(client, self.agency_admin.get_id())
            self.client.get('/request/view_all')
            render_template_patch.assert_called_once_with(
                'request/all.html',
                form=search_requests_form_patch(),
                holidays=sorted(get_holidays_date_list(
                    datetime.utcnow().year,
                    (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
                )
            )

    @patch('app.request.views.SearchRequestsForm')
    @patch('app.request.views.render_template', return_value=jsonify({}))
    def test_view_all_anon(self, render_template_patch, search_requests_form_patch):
        """
        Test render_template in request.views.view_all is called once for anonymous user.
        """
        with self.client:
            self.client.get('/request/view_all')
            render_template_patch.assert_called_once_with(
                'request/all.html',
                form=search_requests_form_patch(),
                holidays=sorted(get_holidays_date_list(
                    datetime.utcnow().year,
                    (datetime.utcnow() + rd(years=DEFAULT_YEARS_HOLIDAY_LIST)).year)
                )
            )

    def test_contact_agency(self):
        response = self.client.post(
            '/request/contact/' + self.request.id,
            data={
                'first_name': 'John',
                'last_name': 'Doris',
                'email': 'doris@email.com',
                'message': 'I need more information about my request.'
            }
        )
        self.assert_flashes(expected_message='Your message has been sent.', expected_category='success')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))

    def test_contact_agency_form_not_validate(self):
        response = self.client.post(
            '/request/contact/' + self.request.id,
            data={
                'first_name': 'John',
                'email': 'doris@email.com',
                'message': 'I need more information about my request.'
            }
        )
        self.assert_flashes(expected_message='There was a problem sending your message. Please try again.',
                            expected_category='danger')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.location).path, url_for('request.view', request_id=self.request.id))


class RequestUtilsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        uf = UserFactory()
        self.rf = RequestFactory()

    @patch('app.request.utils.send_contact_email')
    def test_create_contact_record_anon(self, send_contact_email_patch):
        request = self.rf.create_request_as_anonymous_user()
        first_name = 'John'
        last_name = 'Doris'
        subject = 'Inquire about {}'.format(request.id)
        email = 'doris@email.com'
        message = 'I need more information about my request.'
        body = "Name: {} {}\n\nEmail: {}\n\nSubject: {}\n\nMessage:\n{}".format(
            first_name, last_name, email, subject, message)
        agency_emails = get_agency_emails(request.id)

        create_contact_record(request,
                              first_name,
                              last_name,
                              email,
                              subject,
                              message)
        send_contact_email_patch.assert_called_once_with(
            subject,
            agency_emails,
            message,
            email
        )

        user = Users.query.filter_by(email=email).one()
        self.assertEqual(
            [
                user.first_name,
                user.last_name,
                user.auth_user_type,
                user.email
            ],
            [
                first_name,
                last_name,
                user_type_auth.ANONYMOUS_USER,
                email
            ]
        )
        user_created_event = Events.query.filter(Events.request_id == request.id,
                                                 Events.type == event_type.USER_CREATED).one()
        self.assertEqual(user.val_for_events, user_created_event.new_value)
        email_obj = Emails.query.filter(Emails.request_id == request.id,
                                        Emails.subject == subject).one()
        self.assertEqual(
            [
                [email_obj.to],
                email_obj.body
            ],
            [
                agency_emails,
                body
            ]
        )

        contact_event = Events.query.filter_by(response_id=email_obj.id).one()
        self.assertEqual(
            [
                contact_event.request_id,
                contact_event.user_guid,
                contact_event.auth_user_type,
                contact_event.type,
                contact_event.new_value
            ],
            [
                request.id,
                user.guid,
                user.auth_user_type,
                event_type.CONTACT_EMAIL_SENT,
                email_obj.val_for_events
            ]
        )

    @patch('app.request.utils.send_contact_email')
    def test_create_contact_record_public(self, send_contact_email_patch):
        request = self.rf.create_request_as_public_user()
        user = self.rf.public_user
        subject = 'Inquire about {}'.format(request.id)
        message = 'I need more information about my request.'
        body = "Name: {} {}\n\nEmail: {}\n\nSubject: {}\n\nMessage:\n{}".format(
            user.first_name, user.last_name, user.email, subject, message)
        agency_emails = get_agency_emails(request.id)

        with flask_login_user(user):
            create_contact_record(request,
                                  user.first_name,
                                  user.last_name,
                                  user.email,
                                  subject,
                                  message)
            send_contact_email_patch.assert_called_once_with(
                subject,
                agency_emails,
                message,
                user.email
            )
        email_obj = Emails.query.filter(Emails.request_id == request.id,
                                        Emails.subject == subject).one()
        self.assertEqual(
            [
                [email_obj.to],
                email_obj.body
            ],
            [
                agency_emails,
                body
            ]
        )

        contact_event = Events.query.filter_by(response_id=email_obj.id).one()
        self.assertEqual(
            [
                contact_event.request_id,
                contact_event.user_guid,
                contact_event.auth_user_type,
                contact_event.type,
                contact_event.new_value
            ],
            [
                request.id,
                user.guid,
                user.auth_user_type,
                event_type.CONTACT_EMAIL_SENT,
                email_obj.val_for_events
            ]
        )
