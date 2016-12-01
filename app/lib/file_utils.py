"""
    app.file.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for files

"""
import os
import magic
import paramiko
from functools import wraps
from contextlib import contextmanager
from flask import current_app


def get_mime_type(request_id, filename):
    """
    Gets the mime_type of a file in the uploaded directory using python magic.
    :param request_id: Request ID for the specific file.
    :param filename: the name of the uploaded file.

    :return: mime_type of the file as determined by python magic.
    """

    upload_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'], request_id, filename)
    # TODO: from_file(sftp_gotten_file)
    mime_type = magic.from_file(upload_file, mime=True)
    if current_app.config['MAGIC_FILE'] != '':
        # Check using custom mime database file
        m = magic.Magic(
            magic_file=current_app.config['MAGIC_FILE'],
            mime=True)
        m.from_file(upload_file)
    return mime_type


@contextmanager
def sftp_ctx():
    """
    Context manager that provides an SFTP client object
    (an SFTP session across an open SSH Transport)
    """
    transport = paramiko.Transport((current_app.config['SFTP_HOSTNAME'],
                                    int(current_app.config['SFTP_PORT'])))
    transport.connect(username=current_app.config['SFTP_USERNAME'],
                      pkey=paramiko.RSAKey(filename=current_app.config['SFTP_RSA_KEY_FILE']))
    sftp = paramiko.SFTPClient.from_transport(transport)
    yield sftp
    transport.close()


def _sftp_switch(sftp_func):
    """
    Check if app is using SFTP and, if so, connect to SFTP server
    and call passed function (sftp_func) with connected client,
    otherwise call decorated function (which should be using
    the os library to accomplish the same file-related action).
    """
    def decorator(os_func):
        @wraps(os_func)
        def wrapper(*args, **kwargs):
            if current_app.config['USE_SFTP']:
                with sftp_ctx() as sftp:
                    return sftp_func(sftp, *args, **kwargs)
            else:
                return os_func(*args, **kwargs)
        return wrapper
    return decorator


def _sftp_get_size(sftp, path):
    return sftp.stat(path).st_size


def _sftp_exists(sftp, path):
    try:
        sftp.stat(path)
        return True
    except IOError:
        return False


def _sftp_mkdir(sftp, path):
    return sftp.mkdir(path)


def _sftp_makedirs(sftp, path):
    dirs = []
    while len(path) > 1:
        dirs.append(path)
        path, _ = os.path.split(path)
    while len(dirs):
        dir_ = dirs.pop()
        try:
            sftp.stat(dir_)
        except IOError:
            sftp.mkdir(dir_)


def _sftp_remove(sftp, path):
    sftp.remove(path)


def _sftp_rename(sftp, oldpath, newpath):
    sftp.rename(oldpath, newpath)


@_sftp_switch(_sftp_get_size)
def get_size(path):
    return os.path.getsize(path)


@_sftp_switch(_sftp_exists)
def exists(path):
    return os.path.exists(path)


@_sftp_switch(_sftp_mkdir)
def mkdir(self, path):
    os.mkdir(path)


@_sftp_switch(_sftp_makedirs)
def makedirs(path):
    os.makedirs(path)


@_sftp_switch(_sftp_remove)
def remove(path):
    os.remove(path)


@_sftp_switch(_sftp_rename)
def rename(oldpath, newpath):
    os.rename(oldpath, newpath)
