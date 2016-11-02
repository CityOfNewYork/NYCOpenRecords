import os
import json
import shutil
from unittest.mock import patch

from flask import jsonify, current_app
from tests.lib.base import BaseTestCase
from tests.lib.tools import RequestsFactory
from tests.lib.constants import (
    PNG_FILE_CONTENTS,
    PNG_FILE_SIZE,
)

from app.models import Events
from app.constants import (
    UPDATED_FILE_DIRNAME,
    USER_ID_DELIMITER,
)
from app.constants.event_type import FILE_EDITED
from app.constants.response_privacy import RELEASE_AND_PUBLIC


class ResponseViewsTests(BaseTestCase):

    def setUp(self):
        super(ResponseViewsTests, self).setUp()
        self.request_id = 'FOIL-RVT'
        self.upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.request_id
        )

    def tearDown(self):
        if os.path.exists(self.upload_path):
            shutil.rmtree(self.upload_path)
        super(ResponseViewsTests, self).tearDown()

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
        rf = RequestsFactory(self.request_id)
        response = rf.add_file()

        old_filename = response.metadatas.name
        data_old = {
            'privacy': response.privacy,
            'title': response.metadatas.title,
            'name': old_filename,
            'mime_type': response.metadatas.mime_type,
            'size': response.metadatas.size,
        }

        new_privacy = RELEASE_AND_PUBLIC
        new_filename = 'scream.png'
        new_title = "Updated Title, Shiny and Chrome"
        new_mime_type = 'image/png'
        new_size = PNG_FILE_SIZE
        data_new = {
            'privacy': new_privacy,
            'title': new_title,
            'name': new_filename,
            'mime_type': new_mime_type,
            'size': new_size,
        }

        path = os.path.join(self.upload_path, UPDATED_FILE_DIRNAME)
        os.makedirs(path)
        filepath = os.path.join(path, new_filename)
        with open(filepath, 'wb') as fp:
            fp.write(PNG_FILE_CONTENTS)

        # https://github.com/mattupstate/flask-security/issues/259
        # http://stackoverflow.com/questions/16238462/flask-unit-test-how-to-test-request-from-logged-in-user/16238537#16238537
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = USER_ID_DELIMITER.join((
                    rf.requester.guid, rf.requester.auth_user_type))
                session['_fresh'] = True
            # PUT it in there!
            resp = self.client.put(
                '/response/' + str(response.id),
                data={
                    'privacy': new_privacy,
                    'title': new_title,
                    'filename': new_filename,
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
        # check database (Responses & Metadatas)
        self.assertEqual(
            [
                response.privacy,
                response.metadatas.title,
                response.metadatas.name,
                response.metadatas.mime_type,
                response.metadatas.size
            ],
            [
                new_privacy,
                new_title,
                new_filename,
                new_mime_type,
                new_size
            ])
        # check FILE_EDITED Event created
        events = Events.query.filter_by(response_id=response.id).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(
            [
                event.request_id,
                event.user_id,
                event.auth_user_type,
                event.type,
                event.previous_value,
                event.new_value,
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
        # check file replaced
        self.assertFalse(os.path.exists(
            os.path.join(self.upload_path, old_filename)
        ))
        self.assertFalse(os.path.exists(
            os.path.join(self.upload_path, UPDATED_FILE_DIRNAME, new_filename)
        ))
        self.assertTrue(os.path.exists(
            os.path.join(self.upload_path, new_filename)
        ))

    def test_edit_missing_file(self):
        rf = RequestsFactory(self.request_id)
        response = rf.add_file()
        old_filename = response.metadatas.name
        old = [response.privacy,
               response.metadatas.title,
               old_filename,
               response.metadatas.mime_type,
               response.metadatas.size]
        new_filename = 'bovine.txt'
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = USER_ID_DELIMITER.join((
                    rf.requester.guid, rf.requester.auth_user_type))
                session['_fresh'] = True
            resp = self.client.put(
                '/response/' + str(response.id),
                data={
                    'privacy': RELEASE_AND_PUBLIC,
                    'title': 'The Cow Goes Quack',
                    'filename': new_filename,
                }
            )
        self.assertEqual(
            json.loads(resp.data.decode()),
            {'errors': ["File '{}' not found.".format(new_filename)]}
        )
        # assert nothing was changed or created
        self.assertEqual(
            old,
            [
                response.privacy,
                response.metadatas.title,
                old_filename,
                response.metadatas.mime_type,
                response.metadatas.size
            ]
        )
        self.assertTrue(os.path.exists(
            os.path.join(self.upload_path, old_filename)
        ))
        events = Events.query.filter_by(response_id=response.id).all()
        self.assertFalse(events)
