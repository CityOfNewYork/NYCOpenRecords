import os
import json
import shutil
from unittest.mock import patch
from urllib.parse import urljoin
from datetime import datetime

from flask import (
    current_app,
    url_for,
    request as flask_request,
)
from tests.lib.base import BaseTestCase
from tests.lib.tools import (
    RequestsFactory,
    create_user,
)
from tests.lib.constants import (
    PNG_FILE_NAME,
    PNG_FILE_PATH,
)
from app import email_redis
from app.response.utils import get_email_key
from app.lib.utils import get_file_hash
from app.lib.db_utils import create_object
from app.models import (
    Events,
    ResponseTokens,
)
from app.constants import (
    UPDATED_FILE_DIRNAME,
    DELETED_FILE_DIRNAME,
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

    def test_edit_file(self):
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

        # set email redis object
        email_body = "<p>Email Body</p>"
        redis_key = get_email_key(response.id)
        email_redis.set(redis_key, email_body)

        # https://github.com/mattupstate/flask-security/issues/259
        # http://stackoverflow.com/questions/16238462/flask-unit-test-how-to-test-request-from-logged-in-user/16238537#16238537
        with self.client as client, patch(
            'app.response.utils._send_edit_response_email'  # NOTE: can just set TESTING = True
        ) as send_email_patch:
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
            # check email sent
            send_email_patch.assert_called_once_with(
                rf.request.id, email_body, None)
            # check redis object deleted
            self.assertTrue(email_redis.get(redis_key) is None)

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


    def test_edit_file_missing_file(self):
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

    def test_delete(self):
        rf = RequestsFactory(self.request_id)
        response = rf.add_file()

        with self.client as client, patch(
            'app.response.utils._send_delete_response_email'
        ) as send_email_patch:
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
            # Check file moved to 'deleted' directory
            self.assertFalse(os.path.exists(
                os.path.join(
                    self.upload_path,
                    response.name
                )
            ))
            self.assertTrue(os.path.exists(
                os.path.join(
                    self.upload_path,
                    DELETED_FILE_DIRNAME,
                    response.hash
                )
            ))

            # check email sent
            send_email_patch.assert_called_once_with(rf.request.id, response)


def test_get_content(self):
    rf = RequestsFactory(self.request_id)
    response = rf.add_file()
    unassociated_user = create_user()

    path = '/response/' + str(response.id)
    redirect_url = urljoin(
        flask_request.url_root,
        url_for(
            'auth.index',
            sso2=True,
            return_to=urljoin(flask_request.url_root, path)
        )
    )

    # user not authenticated (redirect)
    resp = self.client.get(path)
    self.assertEqual(resp.location, redirect_url)

    # user authenticated but not associated with request (400)
    with self.client as client:
        with client.session_transaction() as session:
            session['user_id'] = unassociated_user.get_id()
            session['_fresh'] = True
        resp = self.client.get(path)
        self.assertEqual(resp.status_code, 400)

    # user authenticated and associated with request (success)
    with self.client as client:
        with client.session_transaction() as session:
            session['user_id'] = rf.requester.get_id()
            session['_fresh'] = True
        resp = self.client.get(path)
        self.assert_file_sent(resp, rf.request.id, response.name)


def test_get_content_with_token(self):
    rf = RequestsFactory(self.request_id)
    response = rf.add_file()

    valid_token = ResponseTokens(response.id)
    expired_token = ResponseTokens(response.id,
                                   expiration_date=datetime.utcnow())
    create_object(valid_token)
    create_object(expired_token)

    path = '/response/' + str(response.id)

    # invalid token (400)
    resp = self.client.get(path, query_string={'token': 'not_a_real_token'})
    self.assertEqual(resp.status_code, 400)

    # expired token (400)
    resp = self.client.get(path, query_string={'token': expired_token.token})
    self.assertEqual(resp.status_code, 400)
    self.assertTrue(ResponseTokens.query.filter_by(
        token=expired_token.token
    ).first() is None)  # assert response token has been deleted

    # valid token (success)
    resp = self.client.get(path, query_string={'token': valid_token.token})
    self.assert_file_sent(resp, rf.request.id, response.name)


def assert_file_sent(self, flask_response, request_id, filename):
    self.assertEqual(
        flask_response.headers.get('Content-Disposition'),
        "attachment; filename={}".format(filename)
    )
    with open(os.path.join(
            current_app.config["UPLOAD_DIRECTORY"],
            request_id,
            filename
    ), 'rb') as fp:
        self.assertEqual(flask_response.data, fp.read())


def test_get_content_failure(self):
    # no Response
    resp = self.client.get('/response/42')
    self.assertEqual(resp.status_code, 400)

    rf = RequestsFactory()
    response = rf.add_note()
    # wrong Response type
    resp = self.client.get('/response/' + str(response.id))
    self.assertEqual(resp.status_code, 400)
