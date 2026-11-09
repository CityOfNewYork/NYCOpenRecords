"""
    app.file.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Helpers for manipulating files.
    Switches file-handling interface between sftp and os depending on configuration.

"""
import os
import magic
import hashlib
import paramiko
import shutil
from tempfile import TemporaryFile
from functools import wraps
from contextlib import contextmanager
from flask import current_app, send_from_directory, redirect
from app import sentry
from azure.storage.blob import (generate_blob_sas,
                                BlobSasPermissions,
                                BlobServiceClient,
                                BlobClient,
                                ContainerClient
                                )
from datetime import datetime, timedelta

TRANSFER_SIZE_LIMIT = 512000  # 512 kb


class MaxTransferSizeExceededException(Exception):
    pass


class SFTPCredentialsException(Exception):
    pass


@contextmanager
def sftp_ctx():
    """
    Context manager that provides an SFTP client object
    (an SFTP session across an open SSH Transport)
    """
    transport = paramiko.Transport((current_app.config['SFTP_HOSTNAME'],
                                    int(current_app.config['SFTP_PORT'])))
    authentication_kwarg = {}
    if current_app.config['SFTP_PASSWORD']:
        authentication_kwarg['password'] = current_app.config['SFTP_PASSWORD']
    elif current_app.config['SFTP_RSA_KEY_FILE']:
        authentication_kwarg['pkey'] = paramiko.RSAKey(filename=current_app.config['SFTP_RSA_KEY_FILE'])
    else:
        raise SFTPCredentialsException

    transport.connect(username=current_app.config['SFTP_USERNAME'], **authentication_kwarg)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        yield sftp
    except Exception as e:
        sentry.captureException()
        raise paramiko.SFTPError("Exception occurred with SFTP: {}".format(e))
    finally:
        sftp.close()
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


def _raise_if_too_big(bytes_transferred, _):
    if bytes_transferred >= TRANSFER_SIZE_LIMIT:
        raise MaxTransferSizeExceededException


def _sftp_get_size(sftp, path):
    return sftp.stat(path).st_size


def _sftp_exists(sftp, path):
    try:
        sftp.stat(path)
        return True
    except IOError:
        sentry.captureException()
        return False


def _sftp_mkdir(sftp, path):
    return sftp.mkdir(path)


def _sftp_makedirs(sftp, path):
    """ os.makedirs(path, exists_ok=True) """
    dirs = []
    while len(path) > 1:
        dirs.append(path)
        path, _ = os.path.split(path)
    while len(dirs):
        dir_ = dirs.pop()
        try:
            sftp.stat(dir_)
        except IOError:
            sentry.captureException()
            sftp.mkdir(dir_)


def _sftp_remove(sftp, path):
    sftp.remove(path)


def _sftp_rename(sftp, oldpath, newpath):
    sftp.rename(oldpath, newpath)


def _sftp_move(sftp, localpath, remotepath):
    sftp.put(localpath, remotepath)
    os.remove(localpath)


def _sftp_get_mime_type(sftp, path):
    with TemporaryFile() as tmp:
        try:
            sftp.getfo(path, tmp, _raise_if_too_big)
        except MaxTransferSizeExceededException:
            sentry.captureException()
        tmp.seek(0)
        if current_app.config['MAGIC_FILE']:
            # Check using custom mime database file
            m = magic.Magic(
                magic_file=current_app.config['MAGIC_FILE'],
                mime=True)
            mime_type = m.from_buffer(tmp.read())
        else:
            mime_type = magic.from_buffer(tmp.read(), mime=True)
    return mime_type


def _sftp_get_hash(sftp, path):
    sha1 = hashlib.sha1()
    with TemporaryFile() as tmp:
        sftp.getfo(path, tmp)
        tmp.seek(0)
        sha1.update(tmp.read())
    return sha1.hexdigest()


def _sftp_send_file(sftp, directory, filename, **kwargs):
    localpath = _get_file_serving_path(directory, filename)
    if not os.path.exists(localpath):
        sftp.get(os.path.join(directory, filename), localpath)
    return send_from_directory(*os.path.split(localpath), **kwargs)


def _get_file_serving_path(directory, filename):
    """
    Returns the upload serving directory path for a file determined by supplied directory and filename.
    """
    request_id_folder = os.path.basename(directory)
    localpath = os.path.join(current_app.config['UPLOAD_SERVING_DIRECTORY'], request_id_folder)
    if not os.path.exists(localpath):
        os.mkdir(localpath)
    path = os.path.join(request_id_folder, filename)
    return os.path.join(current_app.config['UPLOAD_SERVING_DIRECTORY'], path)


@_sftp_switch(_sftp_get_size)
def getsize(path):
    return os.path.getsize(path)


@_sftp_switch(_sftp_exists)
def exists(path):
    return os.path.exists(path)


@_sftp_switch(_sftp_mkdir)
def mkdir(path):
    os.mkdir(path)


@_sftp_switch(_sftp_makedirs)
def makedirs(path, **kwargs):
    os.makedirs(path, **kwargs)


@_sftp_switch(_sftp_remove)
def remove(path):
    os.remove(path)


@_sftp_switch(_sftp_rename)
def rename(oldpath, newpath):
    os.rename(oldpath, newpath)


@_sftp_switch(_sftp_move)
def move(oldpath, newpath):
    """
    Use this instead of 'rename' if, when using sftp, 'oldpath'
    represents a local file path and 'newpath' a remote path.
    """
    os.rename(oldpath, newpath)


@_sftp_switch(_sftp_get_mime_type)
def get_mime_type(path):
    return os_get_mime_type(path)


def os_get_mime_type(path):
    if current_app.config['MAGIC_FILE']:
        # Check using custom mime database file
        m = magic.Magic(
            magic_file=current_app.config['MAGIC_FILE'],
            mime=True)
        mime_type = m.from_file(path)
    else:
        mime_type = magic.from_file(path, mime=True)
    return mime_type


@_sftp_switch(_sftp_get_hash)
def get_hash(path):
    """
    Returns the sha1 hash of a file a string of
    hexadecimal digits.
    """
    return os_get_hash(path)


def os_get_hash(path):
    sha1 = hashlib.sha1()
    with open(path, 'rb') as fp:
        sha1.update(fp.read())
    return sha1.hexdigest()


@_sftp_switch(_sftp_send_file)
def send_file(directory, filename, **kwargs):
    path = _get_file_serving_path(directory, filename)
    # Move file to data directory if volume storage enabled
    if current_app.config['USE_VOLUME_STORAGE']:
        shutil.copy(os.path.join(directory, filename), path)
    # Serve file from Azure if Azure storage is enabled
    elif current_app.config['USE_AZURE_STORAGE']:
        blob_url = azure_generate_blob_url(os.path.join(directory, filename))
        return redirect(blob_url)
    return send_from_directory(*os.path.split(path), **kwargs)


def create_azure_blob_client(blob_name):
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    return blob_service_client.get_blob_client(container=current_app.config['AZURE_STORAGE_CONTAINER'], blob=blob_name)


def azure_upload(source_path, blob_name):
    blob_client = create_azure_blob_client(blob_name)
    with open(source_path, 'rb') as data:
        blob_client.upload_blob(data, overwrite=True)
    os.remove(source_path)


def azure_generate_blob_url(blob_name):
    # Generate SAS token
    sas_token = generate_blob_sas(account_name=current_app.config['AZURE_STORAGE_ACCOUNT_NAME'],
                                  account_key=current_app.config['AZURE_STORAGE_ACCOUNT_KEY'],
                                  container_name=current_app.config['AZURE_STORAGE_CONTAINER'],
                                  blob_name=blob_name,
                                  permission=BlobSasPermissions(read=True),
                                  expiry=datetime.utcnow() + timedelta(hours=1))

    # Generate blob URL
    url = "https://{0}.blob.core.windows.net/{1}/{2}?{3}".format(
        current_app.config['AZURE_STORAGE_ACCOUNT_NAME'],
        current_app.config['AZURE_STORAGE_CONTAINER'],
        blob_name,
        sas_token)
    return url


def azure_exists(blob_name):
    blob_client = create_azure_blob_client(blob_name)
    return blob_client.exists()


def azure_delete(blob_name):
    blob_client = create_azure_blob_client(blob_name)
    blob_client.delete_blob()


def azure_copy(current_blob_name, new_blob_name):
    blob_client = create_azure_blob_client(new_blob_name)
    url = azure_generate_blob_url(current_blob_name)
    blob_client.start_copy_from_url(url)
