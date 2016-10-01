"""
 .. module:: upload.utils

    :synopsis: Helper functions for uploads
"""

import magic
import subprocess
from .constants import (
    ALLOWED_MIMETYPES,
    MAX_CHUNKSIZE
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


#@task
def start_file_scan(filepath):
    """
    Scans a file and moves it to data directory if it is clean,
    otherwise deletes the file. Updates redis accordingly.

    :param filepath: path of file to be scanned
    """
    # TODO: PIPE output to logfile?
    subprocess.call(['uvscan', filepath])
    # wait and move to /data/directory/
