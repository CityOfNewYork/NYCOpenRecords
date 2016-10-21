import json
from io import BytesIO

from flask import jsonify
from unittest.mock import patch
from tests.base import BaseTestCase
from tests.tools import RequestsFactory


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
        self.assertEqual(
            json.loads(resp.data.decode()),
            {
                'old': {
                    'privacy': old_privacy,
                    'title': old_title,
                },
                'new': {
                    'privacy': "release_public",
                    'title': new_title
                }
            }
        )

        # assert Event
        # assert file changed

    # def test_edit_file_bad()

