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
    prefixed_store as redis,
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

    :return: whether the file type is allowed or not
    """
    is_valid = magic.from_buffer(
        obj.stream.read(MAX_CHUNKSIZE), mime=True
    ) in ALLOWED_MIMETYPES
    obj.stream.seek(0)
    return is_valid


@celery.task
def scan_upload(request_id, filepath):
    """
    Scans an uploaded file and moves it to the data directory
    if it is clean, otherwise deletes the file.
    Updates redis accordingly,

    :param filepath: path of file to be scanned
    """
    filename = os.path.basename(filepath)

    key = get_redis_key_upload(request_id, filename)
    redis.put(key, UPLOAD_STATUS.SCANNING)

    # TODO: PIPE output to logfile (not celery's)? and moar logging
    options = [
        '--analyze',  # Use heuristic analysis to find possible new viruses
        '--atime-preserve'  # Preserve the file's last-accessed time and date
    ]
    cmd = ['uvscan'] + options + [filepath]
    subprocess.call(cmd)

    root, _ = os.path.splitext(filepath)
    is_infected, filepath = _is_file_infected(root, filepath)
    if is_infected:
        os.remove(filepath)
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
        redis.put(key, UPLOAD_STATUS.READY)


def _is_file_infected(root, original_path):
    """
    Checks if the virus scanner has found an infected file.

    When the scanner detects and infected file, it renames the file's extension
    using the following conventions:

    Original    Renamed     Example
    Not v??     v??         file.doc -> file.voc
    v??         vir         file.vbs -> file.vir
    <blank>     vir         file     -> file.vir

    :param root: the file path excluding the file extension
    :param original_path: the unaltered path of an uploaded file
    :return: (Whether the file is infected or not,
        the path to the infected file or the original path)
    """
    path = glob(root + "*")[0]
    _, ext = os.path.splitext(path)
    return original_path != path and ext[1] == 'v', path


def get_redis_key_upload(request_id, upload_filename):
    """

    :param request_id:
    :param upload_filename:
    :return: the formatted key
    """
    # TODO: ensure compatibility with simplekv
    return '_'.join((request_id, upload_filename))
