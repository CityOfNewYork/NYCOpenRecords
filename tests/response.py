import json
from io import BytesIO
from unittest.mock import patch

from flask import jsonify
from tests.base import BaseTestCase
from tests.tools import RequestsFactory

from app.models import Events
from app.constants.event_type import FILE_EDITED


class ResponseViewsTests(BaseTestCase):

    def setUp(self):
        super(ResponseViewsTests, self).setUp()
        # self.request = Request()# CREATE REQUEST

    def test_post_extension(self):
        with patch(
            'app.response.views.add_extension'
        ) as add_extension_patch, patch(
            'app.response.views.redirect', return_value=jsonify({})
        ), patch(
            'app.response.views.url_for'
        ):
            self.client.post(
                '/response/extension/' + 'fake request id',  # self.request.id,
                data={
                    'length': 'foo',
                    'reason': 'bar',
                    'due-date': 'baz',
                    'email-extend-content': 'qux'
                }
            )
            add_extension_patch.assert_called_once_with(
                'fake request id',
                'foo',
                'bar',
                'baz',
                'qux'
            )

    def test_edit_file(self):
        rf = RequestsFactory('FOIL-RVT')
        response, _ = rf.add_file()
        old_privacy = response.privacy
        old_title = response.metadatas.title
        new_filename = 'bovine.txt'
        new_title = "updated title, shiny and chrome"
        data_old = {
            'privacy': old_privacy,
            'title': old_title
        }
        data_new = {
            'privacy': "release_public",
            'title': new_title
        }
        # https://github.com/mattupstate/flask-security/issues/259
        # http://stackoverflow.com/questions/16238462/flask-unit-test-how-to-test-request-from-logged-in-user/16238537#16238537
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = ':'.join((
                    rf.requester.guid, rf.requester.auth_user_type))
                session['_fresh'] = True
            resp = self.client.put(
                '/response/' + str(response.id),
                data={
                    'privacy': "release_public",  # TODO: constant after merge
                    'title': new_title,
                    'file': (BytesIO(b'the cow goes quack'), new_filename)
                }
            )
        # check flask response
        self.assertEqual(
            json.loads(resp.data.decode()),
            {
                'old': data_old,
                'new': data_new
            }
        )
        # check response and metadata edited
        self.assertEqual([response.privacy, response.metadatas.title],
                         ["release_public", new_title])
        # check FILE_EDITED Event created
        event = Events.query.filter_by(response_id=response.id).first()
        self.assertTrue(event)
        self.assertEqual(
            [
                event.request_id,
                event.user_id,
                event.auth_user_type,
                event.type,
                event.previous_response_value,
                event.new_response_value,
            ],
            [
                rf.request.id,
                rf.requester.guid,
                rf.requester.auth_user_type,
                FILE_EDITED,
                data_old,
                data_new,
            ]
        )
        # check EMAIL_NOTIFICATION_SENT Event created
        # assert file changed

    # def test_edit_file_bad()

