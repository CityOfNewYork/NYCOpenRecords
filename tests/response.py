from flask import jsonify
from unittest.mock import patch
from tests.base import BaseTestCase


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
                    'extension-date': 'foo',
                    'reason': 'bar',
                    'due_date': 'baz',
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
