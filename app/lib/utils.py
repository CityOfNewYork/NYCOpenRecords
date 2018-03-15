"""
 .. module: utils

"""

from base64 import b64decode


class InvalidUserException(Exception):
    def __init__(self, user):
        """
        Exception used when an invalid user is detected.

        :param user: the current_user as defined in flask_login
        """
        super(InvalidUserException, self).__init__(
            "Invalid user: {}".format(user))


class UserRequestException(Exception):
    def __init__(self, action, request_id, reason):
        """
        Exception used to handle errors performing actions on a request.

        :param action: Action attempted
        :param request_id: Unique request identifier
        :param reason: Description of failure reason
        """
        super(UserRequestException, self).__init__(
            'Unable to {} request: {}\nReason: {}'.format(action, request_id, reason)
        )


class DuplicateFileException(Exception):
    def __init__(self, file_name, request_id):
        """
        Exception used when a duplicate file is added to a request.

        :param file_name: Name of file uploaded
        :param request_id: Unique request identifier
        """
        super(DuplicateFileException, self).__init__(
            "{} has already been uploaded to {}".format(file_name, request_id)
        )


class PDFCreationException(Exception):
    def __init__(self, pisa_status):
        """
        Exception used when xhtml2pdf fails to create a PDF.

        :param pisa_status: Status / Error message from xhtml2pdf (pisa)
        """
        super(PDFCreationException, self).__init__(
            "Failed to create PDF: \n{}".format(pisa_status)
        )


def b64decode_lenient(data):
    """
    Decodes base64 (bytes or str), padding being optional.

    :param data: a string or bytes-like object of base64 data
    :return: a decoded string
    """
    if isinstance(data, str):
        data = data.encode()
    data += b'=' * (4 - (len(data) % 4))
    return b64decode(data).decode()


def eval_request_bool(val, default=False):
    """
    Evaluates the boolean value of a request parameter.

    :param val: the value to check
    :param default: bool to return by default

    :return: Boolean
    """
    assert isinstance(default, bool)
    if val is not None:
        val = val.lower()
        if val in ['False', 'false', '0', 'n', 'no', 'off']:
            return False
        if val in ['True', 'true', '1', 'y', 'yes', 'on']:
            return True
    return default
