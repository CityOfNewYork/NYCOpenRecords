"""
    app.response.utils
    ~~~~~~~~~~~~~~~~

    synopsis: Handles the functions for responses

"""
from flask_login import current_user
from app.models import Responses, Events
from app.db_utils import create_object
from datetime import datetime
from app.constants import EVENT_TYPE, RESPONSE_TYPE
import json


def add_file():
    """
    Will add a file to the database for the specified request.
    :return:
    """
    # TODO: Implement adding a file
    print("add_file function")

    return None


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


def add_note(request_id, response_content):
    """
    Will add a note to the database for the specified request.
    :return:
    """
    content = json.dumps({"note": response_content})
    process_response(request_id, RESPONSE_TYPE['note'], EVENT_TYPE['note_added'], content)


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


def add_visibility():
    """
    Will add a visibility to the database for the specified request.
    :return:
    """
    # TODO: Implement adding a visiblity
    print("add_visibility function")


def process_response(request_id, response_type, event_type, content, privacy='private'):
    # create response object
    response = Responses(request_id=request_id,
                         type=response_type,
                         date_modified=datetime.utcnow(),
                         content=content,
                         privacy=privacy)
    # store response object
    create_object(obj=response)

    # create event object
    event = Events(request_id=request_id,
                   # user_id=current_user.id,
                   # user_type=current_user.type,
                   type=event_type,
                   timestamp=datetime.utcnow(),
                   response_id=response.id)
    # store event object
    create_object(obj=event)