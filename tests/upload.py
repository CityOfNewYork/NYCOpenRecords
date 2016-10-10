import os
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app import upload_redis as redis
from flask import current_app
from werkzeug.utils import secure_filename

from tests.base import BaseTestCase
from app.upload.utils import get_upload_key
from app.upload.constants import (
    MAX_CHUNKSIZE,
    UPLOAD_STATUS,
)


class UploadViewsTest(BaseTestCase):

    def setUp(self):
        super(UploadViewsTest, self).setUp()
        self.filename = "$ome fi/le.txt"
        self.filename_secure = secure_filename(self.filename)
        self.request_id = 'FOIL-XXX'
        self.quarantine_path = os.path.join(
            current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
            self.request_id,
            self.filename_secure
        )
        self.upload_path = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.request_id,
            self.filename_secure
        )
        self.key = get_upload_key(self.request_id, self.filename_secure)

    def tearDown(self):
        redis.delete(self.key)
        super(UploadViewsTest, self).tearDown()

    @patch('app.upload.views.scan_and_complete_upload.delay')
    def test_post(self, scan_and_complete_patch):
        file_contents = b"contents"
        with scan_and_complete_patch:
            # make request
            response = self.client.post(
                '/upload/' + self.request_id,
                data = {
                    "file": (BytesIO(file_contents), self.filename)
                }
            )
            # check response
            self.assertEqual(
                json.loads(response.data.decode()),
                {
                    "files" : [{
                        "name": self.filename_secure,
                        "original_name": self.filename,
                        "size": len(file_contents)
                    }]
                }
            )
            # checked mocked call
            scan_and_complete_patch.assert_called_once_with(
                self.request_id, self.quarantine_path)
        # check file saved
        self.assertTrue(os.path.exists(self.quarantine_path))
        os.remove(self.quarantine_path)

    @patch('app.upload.views.scan_and_complete_upload.delay')
    def test_post_chunked(self, scan_and_complete_patch):
        full_file_size = MAX_CHUNKSIZE * 2
        with scan_and_complete_patch:
            # first chunk
            response = self.client.post(
                '/upload/' + self.request_id,
                data={
                    "file": (BytesIO(b"0" * MAX_CHUNKSIZE), self.filename)
                },
                headers={
                    "Content-Range": "bytes 0-511999/1024000"
                }
            )
            self.assertEqual(
                json.loads(response.data.decode()),
                {
                    "files": [{
                        "name": self.filename_secure,
                        "original_name": self.filename,
                        "size": MAX_CHUNKSIZE
                    }]
                }
            )
            self.assertEqual(os.path.getsize(self.quarantine_path),
                             MAX_CHUNKSIZE)
            # second chunk
            response = self.client.post(
                '/upload/' + self.request_id,
                data={
                    "file": (BytesIO(b"0" * MAX_CHUNKSIZE), self.filename)
                },
                headers={
                    "Content-Range": "bytes 512000-1023999/1024000"
                }
            )
            self.assertEqual(
                json.loads(response.data.decode()),
                {
                    "files": [{
                        "name": self.filename_secure,
                        "original_name": self.filename,
                        "size": full_file_size
                    }]
                }
            )
            self.assertEqual(os.path.getsize(self.quarantine_path),
                             full_file_size)
            scan_and_complete_patch.assert_called_once_with(
                self.request_id, self.quarantine_path)
            os.remove(self.quarantine_path)

    def test_post_invalid_mime(self):
        response = self.client.post(
            '/upload/' + self.request_id,
            data={
                "file": (BytesIO(b"#!/usr/bin/python\n"), self.filename)
            }
        )
        self.assertEqual(
            json.loads(response.data.decode()),
            {
                "files": [{
                    "name": self.filename_secure,
                    "error": "File type 'text/x-python' is not allowed."
                }]
            }
        )

    def test_delete_request_id(self):
        endpoint = '/upload/request/{}/{}'.format(
            self.request_id,
            self.filename_secure  # FIXME: encoded filename
        )
        expected_response = {
            "deleted": self.filename_secure
        }

        # test for data/quarantine/
        open(self.quarantine_path, 'w').close()
        redis.set(self.key, UPLOAD_STATUS.SCANNING)
        response = self.client.delete(endpoint)
        self.assertEqual(
            json.loads(response.data.decode()),
            expected_response
        )
        self.assertFalse(os.path.exists(self.quarantine_path))

        # test for data/
        open(self.upload_path, 'w').close()
        redis.set(self.key, UPLOAD_STATUS.READY)
        response = self.client.delete(endpoint)
        self.assertEqual(
            json.loads(response.data.decode()),
            expected_response
        )
        self.assertFalse(os.path.exists(self.upload_path))

    def test_delete_response_id(self):
        pass

    def test_status(self):
        # bad file name
        response = self.client.get(
            '/upload/status',
            query_string={
                "request_id": self.request_id,
                "filename": "non-existent-file.txt"
            }
        )
        self.assertEqual(
            json.loads(response.data.decode()),
            {
                "error": "Upload status not found."
            }
        )
        # good file name
        redis.set(self.key, UPLOAD_STATUS.PROCESSING)
        response = self.client.get(
            '/upload/status',
            query_string={
                "request_id": self.request_id,
                "filename": self.filename
            }
        )
        self.assertEqual(
            json.loads(response.data.decode()),
            {
                "status": UPLOAD_STATUS.PROCESSING
            }
        )


class UploadTestUtils(BaseTestCase):
    pass


if __name__ == "__main__":
    unittest.main()
