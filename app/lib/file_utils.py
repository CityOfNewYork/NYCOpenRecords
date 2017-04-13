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
import nacl.secret
from io import BytesIO
from tempfile import TemporaryFile
from functools import wraps
from contextlib import contextmanager
from flask import current_app, send_from_directory

TRANSFER_SIZE_LIMIT = 512000  # 512 kb
FILE_READ_SIZE_LIMIT = 10000000  # 10 mb


# Encryption -----------------------------------------------------------------------------------------------------------

class DecryptKeyException(Exception):
    """ Raised on failure when decrypting decryption key. """
    pass


class FileCrypter(object):
    CHUNKSIZE = 10000000  # 10 mb
    LEN_ENCRYPTED_DIFF = 40

    def __init__(self, chunksize=CHUNKSIZE):
        self.__box = nacl.secret.SecretBox(self.__key)
        self.__chunksize_encrypt = chunksize
        self.__chunksize_decrypt = chunksize + self.LEN_ENCRYPTED_DIFF

    def encrypt(self, src, dest):
        """
        Save a encrypted version of a file to a desired location.

        :param src: source path of file to encrypt
        :param dest: destination file path
        """
        self.__crypt(src, dest, self.__box.encrypt)

    def decrypt(self, src, dest):
        """
        Save a decrypted version of a file to a desired location.

        :param src: source path of file to encrypt
        :param dest: destination file path
        """
        self.__crypt(src, dest, self.__box.decrypt)

    def __crypt(self, src, dest, method):
        """
        Encrypt or Decrypt a source file and write to a destination file in chunks.

        :param src: source file path
        :param dest: destination file path
        :param method: self.__box.decrypt or self.__box.encrypt
        """
        assert src != dest, "Encryption source and destination must differ."
        with open(src, "rb") as src_, open(dest, "wb") as dest_:
            chunksize = self.__chunksize_encrypt if method == self.__box.encrypt else self.__chunksize_decrypt
            for chunk in iter(lambda: src_.read(chunksize), b''):
                dest_.write(method(chunk))

    @property
    def __key(self):
        key_filename = current_app.config["FILE_ENCRYPTION_KEY_FILE"]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            "10.132.41.210",
            username="palisand",
            pkey=paramiko.RSAKey(filename="/home/vagrant/.ssh/id_rsa")
        )

        # copy encrypted key file to server
        sftp = ssh.open_sftp()
        sftp.put(key_filename, key_filename)

        # create unencrypted key file on server
        cmd = "/usr/local/bin/gpg --batch --quiet --yes --passphrase password {}".format(key_filename)
        _, stdout, stderr = ssh.exec_command(cmd)

        # check for and raise if command failed
        err = stderr.read()
        if err:
            sftp.close()
            ssh.close()
            raise DecryptKeyException(err)
        else:
            # retrieve unencrypted key file contents
            with BytesIO() as fp:
                sftp.getfo("key", fp)  # FIXME: magic "key"
                fp.seek(os.SEEK_SET)
                key = fp.read().rstrip()
            # remove key files from server
            sftp.remove("key")
            sftp.remove(key_filename)
            sftp.close()
            ssh.close()

        return key


def _use_decrypter(os_func):
    """
    Check if app is using FILE_ENCRYPTION and, if so, perform the necessary
    decryption before calling os_func with a path to a temporary unencrypted file.

    :param os_func: function using the os module to perform some file-related 
        activity that involves retrieving data/metadata from a single file
        * MUST have the signature "os_func(path)" *
    """
    @wraps(os_func)
    def wrapper(path):
        if current_app.config['USE_FILE_ENCRYPTION']:
            crypter = FileCrypter()
            with TemporaryFile() as tmp:
                crypter.decrypt(path, tmp.name)
                os_func(path)
        else:
            os_func(path)

    return wrapper


def _rename_and_encrypt(rename_func):
    """
    Check if app is using FILE_ENCRYPTION and, if so, rather than
    calling rename_func, save an encrypted version of a provided source
    file into a destination file and delete the source file.
    
    :param rename_func: function that calls os.rename with 
        ONLY its first 2 arguments (src, dest)
    """
    @wraps(rename_func)
    def wrapper(oldpath, newpath):
        if current_app.config['USE_FILE_ENCRYPTION']:
            crypter = FileCrypter()
            crypter.encrypt(oldpath, newpath)
            os.remove(oldpath)
        else:
            rename_func(oldpath, newpath)
    return wrapper


# SFTP -----------------------------------------------------------------------------------------------------------------

class MaxTransferSizeExceededException(Exception):
    """ Raised when exceeding upper limit on SFTP transfer size. """
    pass


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
    try:
        yield sftp
    except Exception as e:
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
        """
        :param os_func: function using the os module to perform some file-related activity 
        """
        @wraps(os_func)
        def wrapper(*args, **kwargs):
            if current_app.config['USE_SFTP'] and not current_app.config['USE_FILE_ENCRYPTION']:
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
            pass
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
    request_id_folder = os.path.basename(directory)
    localpath = os.path.join(current_app.config['UPLOAD_SERVING_DIRECTORY'], request_id_folder)
    if not os.path.exists(localpath):
        os.mkdir(localpath)
    path = os.path.join(request_id_folder, filename)
    localpath = os.path.join(current_app.config['UPLOAD_SERVING_DIRECTORY'], path)
    if not os.path.exists(localpath):
        sftp.get(os.path.join(directory, filename), localpath)
    return send_from_directory(*os.path.split(localpath), **kwargs)


# OS -------------------------------------------------------------------------------------------------------------------

@_use_decrypter
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


@_rename_and_encrypt
@_sftp_switch(_sftp_rename)
def rename(oldpath, newpath):
    os.rename(oldpath, newpath)


@_rename_and_encrypt
@_sftp_switch(_sftp_move)
def move(oldpath, newpath):
    """
    Use this instead of 'rename' if, when using sftp, 'oldpath'
    represents a local file path and 'newpath' a remote path.
    """
    os.rename(oldpath, newpath)


@_use_decrypter
@_sftp_switch(_sftp_get_mime_type)
def get_mime_type(path):
    """
    Returns the mimetype of a file (e.g. "img/png").
    """
    return os_get_mime_type(path)


def os_get_mime_type(path):
    """ 
    * WARNING: This should only be used for files in quarantine (unencrypted or on app server)! * 
    """
    if current_app.config['MAGIC_FILE']:
        # Check using custom mime database file
        m = magic.Magic(
            magic_file=current_app.config['MAGIC_FILE'],
            mime=True)
        mime_type = m.from_file(path)
    else:
        mime_type = magic.from_file(path, mime=True)
    return mime_type


@_use_decrypter
@_sftp_switch(_sftp_get_hash)
def get_hash(path):
    """
    Returns the sha1 hash of a file as a string of hexadecimal digits.
    """
    return os_get_hash(path)


def os_get_hash(path):
    """
    * WARNING: This should only be used for files in quarantine (unencrypted or on app server)! *
    """
    sha1 = hashlib.sha1()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(FILE_READ_SIZE_LIMIT), b''):  # TODO: test this
            sha1.update(chunk)
    return sha1.hexdigest()


@_use_decrypter
@_sftp_switch(_sftp_send_file)
def send_file(path, **kwargs):
    return send_from_directory(os.path.dirname(path), os.path.basename(path), **kwargs)
