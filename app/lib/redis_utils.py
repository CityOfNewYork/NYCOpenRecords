import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

from flask import current_app
from app import upload_redis as redis
from app.lib.file_utils import (
    os_get_hash,
    os_get_mime_type
)
from flask_kvsession import (
    KVSession
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


# Redis Session Utilities
def redis_get_user_session(session_id):
    serialization_method = pickle
    session_class = KVSession

    s = session_class(serialization_method.loads(
        current_app.kvsession_store.get(session_id)
    ))
    s.sid_s = session_id

    return s


def redis_delete_user_session(session_id):
    redis.delete(session_id)
