import os
import json
import shutil
import unittest
from io import BytesIO
from base64 import b64encode
from unittest.mock import patch

from app import upload_redis as redis
from flask import current_app
from werkzeug.utils import secure_filename

from tests.base import BaseTestCase
from app.upload.utils import (
    get_upload_key,
    VirusDetectedException,
    scan_and_complete_upload,
)
from app.upload.constants import (
    MAX_CHUNKSIZE,
    upload_status,
)


class UploadViewsTests(BaseTestCase):

    def setUp(self):
        super(UploadViewsTests, self).setUp()
        self.filename = "$ome fi/le.txt"
        self.filename_secure = secure_filename(self.filename)
        self.request_id = 'FOIL-TEST-UVT'
        self.quarantine_basepath = os.path.join(
            current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
            self.request_id
        )
        self.quarantine_path = os.path.join(
            self.quarantine_basepath,
            self.filename_secure
        )
        self.upload_basepath = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.request_id
        )
        self.upload_path = os.path.join(
            self.upload_basepath,
            self.filename_secure
        )
        self.key = get_upload_key(self.request_id, self.filename_secure)

    def tearDown(self):
        redis.delete(self.key)
        if os.path.exists(self.quarantine_basepath):
            shutil.rmtree(self.quarantine_basepath)
        if os.path.exists(self.upload_basepath):
            shutil.rmtree(self.upload_basepath)
        super(UploadViewsTests, self).tearDown()

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

    def test_post_existing_file(self):
        os.mkdir(self.upload_basepath)
        open(self.upload_path, 'w').close()
        response = self.client.post(
            '/upload/' + self.request_id,
            data={
                "file": (BytesIO(b""), self.filename)
            }
        )
        self.assertEqual(
            json.loads(response.data.decode()),
            {
                "files": [{
                    "name": self.filename_secure,
                    "error": "A file with this name has already "
                             "been uploaded for this request."
                }]
            }
        )
        # make sure file wasn't deleted
        self.assertTrue(os.path.exists(self.upload_path))

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
                    "error": "The file type 'text/x-python' is not allowed."
                }]
            }
        )

    def test_delete_request_id(self):
        endpoint = '/upload/request/{}/{}'.format(
            self.request_id,
            b64encode(self.filename_secure.encode()).decode().strip('=')
        )
        expected_response = {
            "deleted": self.filename_secure
        }

        # test for data/quarantine/
        os.mkdir(self.quarantine_basepath)
        open(self.quarantine_path, 'w').close()
        redis.set(self.key, upload_status.SCANNING)
        response = self.client.delete(endpoint)
        self.assertEqual(
            json.loads(response.data.decode()),
            expected_response
        )
        self.assertFalse(os.path.exists(self.quarantine_path))

        # test for data/
        os.mkdir(self.upload_basepath)
        open(self.upload_path, 'w').close()
        redis.set(self.key, upload_status.READY)
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
        redis.set(self.key, upload_status.PROCESSING)
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
                "status": upload_status.PROCESSING
            }
        )


class UploadUtilsTests(BaseTestCase):

    def setUp(self):
        super(UploadUtilsTests, self).setUp()
        self.request_id = 'FOIL-TEST-UUT'
        self.filename = "iamafile.txt"
        self.quarantine_basepath = os.path.join(
            current_app.config['UPLOAD_QUARANTINE_DIRECTORY'],
            self.request_id
        )
        self.quarantine_path = os.path.join(
            self.quarantine_basepath,
            self.filename
        )
        self.upload_basepath = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            self.request_id,
        )
        self.upload_path = os.path.join(
            self.upload_basepath,
            self.filename
        )
        os.mkdir(self.quarantine_basepath)
        os.mkdir(self.upload_basepath)
        open(self.quarantine_path, 'w').close()
        self.key = get_upload_key(self.request_id, self.filename)

    def tearDown(self):
        redis.delete(self.key)
        shutil.rmtree(self.quarantine_basepath)
        shutil.rmtree(self.upload_basepath)
        super(UploadUtilsTests, self).tearDown()

    def test_scan_good_file(self):
        scan_and_complete_upload(self.request_id, self.quarantine_path)
        self.assertFalse(os.path.exists(self.quarantine_path))
        self.assertTrue(os.path.exists(self.upload_path))
        self.assertEqual(redis.get(self.key).decode(), upload_status.READY)

    def test_scan_bad_file(self):
        with patch(
            'app.upload.utils.scan_file', side_effect=fake_scan_file
        ):
            scan_and_complete_upload(self.request_id, self.quarantine_path)
            self.assertFalse(os.path.exists(self.quarantine_path))
            self.assertFalse(os.path.exists(self.upload_path))
            self.assertFalse(redis.exists(self.key))


def fake_scan_file(filepath):
    os.remove(filepath)
    raise VirusDetectedException(filepath)


if __name__ == "__main__":
    unittest.main()
