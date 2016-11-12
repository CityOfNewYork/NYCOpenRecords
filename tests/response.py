import os
import json
import shutil
from unittest.mock import patch

from flask import jsonify, current_app
from tests.lib.base import BaseTestCase
from tests.lib.tools import RequestsFactory
from tests.lib.constants import (
    PNG_FILE_NAME,
    PNG_FILE_PATH,
)
from app.lib.utils import get_file_hash
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


    def test_edit_response_file(self):
        rf = RequestsFactory(self.request_id)
        response = rf.add_file()

        old_filename = response.name
        data_old = {
            'privacy': response.privacy,
            'title': response.title,
            'name': old_filename,
            'mime_type': response.mime_type,
            'size': response.size,
            'hash': response.hash,
        }

        new_privacy = RELEASE_AND_PUBLIC
        new_filename = PNG_FILE_NAME
        new_title = "Updated Title, Shiny and Chrome"
        new_mime_type = 'image/png'
        new_size = os.path.getsize(PNG_FILE_PATH)
        new_hash = get_file_hash(PNG_FILE_PATH)
        data_new = {
            'privacy': new_privacy,
            'title': new_title,
            'name': new_filename,
            'mime_type': new_mime_type,
            'size': new_size,
            'hash': new_hash,
        }

        # copy test file into proper directory
        path = os.path.join(self.upload_path, UPDATED_FILE_DIRNAME)
        os.makedirs(path)
        filepath = os.path.join(path, new_filename)
        shutil.copyfile(PNG_FILE_PATH, filepath)

        # https://github.com/mattupstate/flask-security/issues/259
        # http://stackoverflow.com/questions/16238462/flask-unit-test-how-to-test-request-from-logged-in-user/16238537#16238537
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = rf.requester.get_id()
                session['_fresh'] = True
            # PUT it in there!
            resp = self.client.patch(
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
                response.title,
                response.name,
                response.mime_type,
                response.size,
                response.hash,
            ],
            [
                new_privacy,
                new_title,
                new_filename,
                new_mime_type,
                new_size,
                new_hash,
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

        # TODO: test proper email sent

    def test_edit_response_file_missing_file(self):
        rf = RequestsFactory(self.request_id)
        response = rf.add_file()
        old_filename = response.name
        old = [response.privacy,
               response.title,
               old_filename,
               response.mime_type,
               response.size,
               response.deleted]
        new_filename = 'bovine.txt'
        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = rf.requester.get_id()
                session['_fresh'] = True
            resp = self.client.patch(
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
                response.title,
                old_filename,
                response.mime_type,
                response.size,
                response.deleted,
            ]
        )
        self.assertTrue(os.path.exists(
            os.path.join(self.upload_path, old_filename)
        ))
        events = Events.query.filter_by(response_id=response.id).all()
        self.assertFalse(events)

    def test_delete_response(self):
        rf = RequestsFactory(self.request_id)
        response = rf.add_note()

        with self.client as client:
            with client.session_transaction() as session:
                session['user_id'] = rf.requester.get_id()
                session['_fresh'] = True
            resp_bad_1 = self.client.patch(
                '/response/' + str(response.id),
                data={
                    'deleted': True,
                    'confirmation': 'invalid'
                }
            )

            self.assertEqual(
                json.loads(resp_bad_1.data.decode()),
                {"message": "No changes detected."}
            )
            self.assertFalse(response.deleted)

            resp_bad_2 = self.client.patch(
                '/response/' + str(response.id),
                data={
                    'deleted': True,
                    # confirmation missing
                }
            )

            self.assertEqual(
                json.loads(resp_bad_2.data.decode()),
                {"message": "No changes detected."}
            )
            self.assertFalse(response.deleted)

            resp_good = self.client.patch(
                '/response/' + str(response.id),
                data={
                    'deleted': True,
                    'confirmation': ':'.join((rf.request.id, str(response.id)))
                }
            )

            self.assertEquals(
                json.loads(resp_good.data.decode()),
                {
                    'old': {
                        'deleted': 'False'
                    },
                    'new': {
                        'deleted': 'True'
                    }
                }
            )
            self.assertTrue(response.deleted)

        # TODO: test proper email sent
