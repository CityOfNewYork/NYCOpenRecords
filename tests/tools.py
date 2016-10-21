import os
import uuid

from datetime import datetime

from flask import current_app
from app.constants import (
    ACKNOWLEDGEMENT_DAYS_DUE,
    response_type,
    PUBLIC_USER_NYC_ID,
)
from app.constants.response_privacy import PRIVATE
from app.models import (
    Requests,
    Responses,
    Files,
    Users,
)
from app.request.utils import generate_request_id
from app.lib.date_utils import (
    get_following_date,
    get_due_date
)
from app.lib.db_utils import create_object


class RequestsFactory(object):
    """
    A very crude first step in making testing easier.
    """

    filepaths = []

    def __init__(self, request_id):
        date_created = datetime.utcnow()
        date_submitted = get_following_date(date_created)
        agency_ein = 2
        self.request = Requests(
            request_id or generate_request_id(agency_ein),
            title="I would like my vital essence.",
            description="Someone has taken my vital essence "
            "and I would like it back.",
            agency_ein=agency_ein,
            date_created=date_created,
            date_submitted=date_submitted,
            due_date=get_due_date(date_submitted,
                                  ACKNOWLEDGEMENT_DAYS_DUE),
            submission='Direct Input',
            current_status='Open')
        create_object(self.request)
        self.requester = Users(
            guid='abc123',
            auth_user_type=PUBLIC_USER_NYC_ID,
            agency=agency_ein,
            first_name='Jane',
            last_name='Doe',
            email='jdizzle@email.com',
            email_validated=True,
            terms_of_use_accepted=True,
            title='The Janest')
        create_object(self.requester)
        # TODO: UserRequests obj

    def add_file(self,
                 filepath=None,
                 mime_type='text/plain',
                 title=None):
        if filepath is None:
            filename = str(uuid.uuid4())
            filepath = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                    self.request.id,
                                    filename)
        else:
            filename = os.path.basename(filepath)

        self.filepaths.append(filepath)

        # create an empty file if the specified path does not exist
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            open(filepath, 'w').close()

        file_ = Files(
            name=filename,
            mime_type=mime_type,
            title=title or filename,
            size=os.path.getsize(filepath)
        )
        create_object(file_)
        response = Responses(
            request_id=self.request.id,
            type=response_type.FILE,
            date_modified=datetime.utcnow(),
            metadata_id=file_.id,
            privacy=PRIVATE,
        )
        # TODO: add Events FILE_ADDED
        create_object(response)
        return response, file_

    def add_note(self):
        pass

    def __del__(self):
        """
        Clean up time!
        - remove any files created by this factory
        - ...
        """
        for path in self.filepaths:
            if os.path.exists(path):
                os.remove(path)
