"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
from flask_login import current_user
from app.models import Responses, Events, Notes, Files
from app.db_utils import create_object
from datetime import datetime
from app.constants import EVENT_TYPE, RESPONSE_TYPE
import os
import magic


def add_file(request_id, upload_file):
    """
    Will add a file to the database for the specified request.
    :return:
    """
    size = os.path.getsize(upload_file)
    mime_type = magic.from_file(upload_file, mime=True)
    files = Files(name='test', mime_type=mime_type, title='title', size=size)
    create_object(obj=files)
    process_response(request_id, RESPONSE_TYPE['file'], EVENT_TYPE['file_added'], files.metadata_id)


def delete_file():
    """
    Will delete a file in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a file
    print("delete_file function")

    return None


def edit_file():
    """
    Will edit a file to the database for the specified request.
    :return:
    """
    # TODO: Implement editing a file
    print("edit_file function")


def add_note(request_id, content):
    """

    :param request_id: takes in FOIL request ID as an argument for the process_response function
    :param content: content of the note to be created and stored as a note object
    :return: Stores the note content into the Notes table.
             Provides parameters for the process_response function to create and store responses and events object.
    """
    note = Notes(content=content)
    create_object(obj=note)
    process_response(request_id, RESPONSE_TYPE['note'], EVENT_TYPE['note_added'], note.metadata_id)


def delete_note():
    """
    Will delete a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("delete_note function")


def edit_note():
    """
    Will edit a note in the database for the specified request.
    :return:
    """
    # TODO: Implement deleting a note
    print("edit_note function")


def add_extension():
    """
    Will add an extension to the database for the specified request.
    :return:
    """
    # TODO: Implement adding an extension
    print("add_extension function")


def edit_extension():
    """
    Will edit an extension to the database for the specified request.
    :return:
    """
    # TODO: Implement editing an extension
    print("edit_extension function")


def add_email():
    """
    Will add an email to the database for the specified request.
    :return:
    """
    # TODO: Implement adding an email
    print("add_email function")


def add_sms():
    """
    Will add an SMS to the database for the specified request.
    :return:
    """
    # TODO: Implement adding an SMS
    print("add_sms function")


def add_push():
    """
    Will add a push to the database for the specified request.
    :return:
    """
    # TODO: Implement adding a push
    print("add_push function")


def process_response(request_id, response_type, event_type, metadata_id, privacy='private'):
    """
    Creates and stores responses and events objects to the database

    :param request_id: FOIL request ID to be stored into the responses and events tables
    :param response_type: type of response to be stored in the responses table
    :param event_type: type of event to be stored in the events table
    :param metadata_id: metadata_id of the specific response to be stored in the responses table
    :param privacy: privacy of the response (default is 'private') to be stored in the responses table
    :return: Creates and stores response object with given arguments from separate response type functions.
             Creates and stores events object to the database.
    """
    # create response object
    response = Responses(request_id=request_id,
                         type=response_type,
                         date_modified=datetime.utcnow(),
                         metadata_id=metadata_id,
                         privacy=privacy)
    # store response object
    create_object(obj=response)

    # create event object
    event = Events(request_id=request_id,
                   # user_id and user_type currently commented out for testing
                   # will need in production to store user information in events table
                   # will this be called for anonymous user?
                   # user_id=current_user.id,
                   # user_type=current_user.type,
                   type=event_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id)
    # store event object
    create_object(obj=event)
