"""
    app.file)utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for files

"""
from flask import current_app
import magic
import os


def get_mime_type(request_id, filename):
    """
    Gets the mime_type of a file in the uploaded directory using python magic.
    :param request_id: Request ID for the specific file.
    :param filename: the name of the uploaded file.

    :return: mime_type of the file as determined by python magic.
    """
    upload_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'] + request_id, filename)
    mime_type = magic.from_file(upload_file, mime=True)
    return mime_type
