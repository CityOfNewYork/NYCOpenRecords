import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

from app import upload_redis as redis
from app.lib.file_utils import (
    os_get_hash,
    os_get_mime_type
)


# Redis File Utilities
def redis_set_file_metadata(request_or_response_id, filepath, is_update=False):
    """
    Stores a file's size, mime type, and hash.
    """
    redis.set(
        _get_file_metadata_key(request_or_response_id, filepath, is_update),
        ':'.join((
            str(os.path.getsize(filepath)),
            os_get_mime_type(filepath),
            os_get_hash(filepath)
        ))
    )


def redis_get_file_metadata(request_or_response_id, filepath, is_update=False):
    """
    Returns a tuple containing a file's
        ( size (int), mime type (str), and hash (str) ).
    """
    data = redis.get(_get_file_metadata_key(
        request_or_response_id, filepath, is_update)).decode().split(':')
    data[0] = int(data[0])  # size
    return tuple(data)


def redis_delete_file_metadata(request_or_response_id, filepath, is_update=False):
    redis.delete(_get_file_metadata_key(
        request_or_response_id, filepath, is_update))


def _get_file_metadata_key(request_or_response_id, filepath, is_update):
    """
    See upload.utils.get_upload_key

    Since this key is being stored in upload_redis, a pipe
    is used instead of an underscore to avoid any key conflicts.
    """
    return '|'.join((str(request_or_response_id),
                     os.path.basename(filepath),
                     'update' if is_update else 'new'))
