"""
    app.file.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for files

"""
from flask import current_app
import magic
import os
from app.upload.constants import ALLOWED_MIMETYPES


def get_mime_type(request_id, filename):
    """
    Gets the mime_type of a file in the uploaded directory using python magic.
    :param request_id: Request ID for the specific file.
    :param filename: the name of the uploaded file.

    :return: mime_type of the file as determined by python magic.
    """

    upload_file = os.path.join(current_app.config['UPLOAD_DIRECTORY'], request_id, filename)
    mime_type = magic.from_file(upload_file, mime=True)
    is_valid = mime_type in ALLOWED_MIMETYPES
    if is_valid:
        mime_type = magic.from_file(upload_file, mime=True)
        is_valid = mime_type in ALLOWED_MIMETYPES
        if is_valid and current_app.config['MAGIC_FILE'] != '':
            # 3. Check using custom mime database file
            m = magic.Magic(
                magic_file=current_app.config['MAGIC_FILE'],
                mime=True)
            m.from_file(upload_file)
            is_valid = mime_type in ALLOWED_MIMETYPES
        # obj.stream.seek(0)
    return is_valid, mime_type
    # return mime_type
