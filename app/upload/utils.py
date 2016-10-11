"""
 .. module:: upload.utils

    :synopsis: Helper functions for uploads
"""

import os
import magic
import subprocess
from glob import glob
from flask import current_app
from .constants import (
    ALLOWED_MIMETYPES,
    MAX_CHUNKSIZE,
    UPLOAD_STATUS,
)
from app import (
    celery,
    upload_redis as redis
)


def parse_content_range(header):
    """
    Extracts the starting byte position and resource length.

    Content-Range = "Content-Range" ":" content-range-spec

    content-range-spec      = byte-content-range-spec
    byte-content-range-spec = bytes-unit SP
                              byte-range-resp-spec "/"
                              ( instance-length | "*" )
    byte-range-resp-spec    = (first-byte-pos "-" last-byte-pos)
                                  | "*"
    instance-length         = 1*DIGIT

    :param header: the rhs of the content-range header
    :return: the first-byte-pos and instance-length
    """
    bytes = header.split(' ')[1]
    return int(bytes.split('-')[0]), int(bytes.split('/')[1])


def is_valid_file_type(obj):
    """
    Validates the mime type of a file.

    :param obj: the file storage object to check
    :type obj: werkzeug.datastructures.FileStorage

    :return: (whether the mime type is allowed or not,
        the mime type)
    """
    # 1. Check content type header
    mime_type = obj.content_type
    is_valid = mime_type in ALLOWED_MIMETYPES
    if is_valid:
        buffer = obj.stream.read(MAX_CHUNKSIZE)
        # 2. Check from file buffer
        mime_type = magic.from_buffer(buffer, mime=True)
        is_valid = mime_type in ALLOWED_MIMETYPES
        # if is_valid:
        #     # 3. Check using mime database file
        #     m = magic.Magic(
        #         magic_file=current_app.config['MAGIC_FILE'],
        #         mime=True)
        #     m.from_buffer(buffer)
        #     is_valid = mime_type in ALLOWED_MIMETYPES
        obj.stream.seek(0)
    return is_valid, mime_type


def get_upload_key(request_id, upload_filename):
    """
    Returns a formatted key for an upload.
    Intended for tracking the status of an upload.

    :param request_id: id of the request associated with the upload
    :param upload_filename: the name of the uploaded file

    :return: the formatted key
    """
    return '_'.join((request_id, upload_filename))


class VirusDetectedException(Exception):
    """
    Raise when scanner detects an infected file.
    """
    def __init__(self, filename):
        super(VirusDetectedException, self).__init__(
            "Infected file '{}' removed.".format(filename))


@celery.task
def scan_and_complete_upload(request_id, filepath):
    """
    Scans an uploaded file (see scan_file) and moves
    it to the data directory if it is clean.
    Updates redis accordingly.

    :param request_id: id of request associated with the upload
    :param filepath: path to uploaded and quarantined file
    """
    filename = os.path.basename(filepath)

    key = get_upload_key(request_id, filename)
    redis.set(key, UPLOAD_STATUS.SCANNING)

    try:
        scan_file(filepath)
    except VirusDetectedException:
        redis.delete(key)
    else:
        # complete upload
        dst_dir = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            request_id
        )
        if not os.path.exists(dst_dir):
            os.mkdir(dst_dir)
        os.rename(
            filepath,
            os.path.join(dst_dir, filename)
        )
        redis.set(key, UPLOAD_STATUS.READY)


def scan_file(filepath):
    """
    Scans a file for viruses using McAfee Virus Scan. If an infected
    file is detected, removes the file and raises VirusDetectedException.

    :param filepath: path of file to scan
    """
    if current_app.config['VIRUS_SCAN_ENABLED']:
        options = [
            '--analyze',  # Use heuristic analysis to find possible new viruses
            '--atime-preserve',  # Preserve the file's last-accessed time and date
            '--delete'  # Automatically delete the infected file
        ]
        cmd = ['uvscan'] + options + [filepath]
        subprocess.call(cmd)  # TODO: redirect output to logfile
        # if the file was removed, it was infected
        if not os.path.exists(filepath):
            raise VirusDetectedException(os.path.basename(filepath))
