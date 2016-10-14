import os
import uuid

from datetime import datetime

from flask import current_app
from app.constants import (
    ACKNOWLEDGEMENT_DAYS_DUE,
    response_type,
)
from app.models import (
    Requests,
    Responses,
    Files,
)
from app.request.utils import (
    generate_request_id,
    get_date_submitted,
    get_due_date
)
from app.db_utils import create_object


class RequestsFactory(object):
    """
    A very crude first step in making testing easier.
    """

    def __init__(self, request_id):
        date_created = datetime.utcnow()
        date_submitted = get_date_submitted(date_created)
        agency_ein = 2
        self.request = Requests(
            request_id or generate_request_id(agency_ein),
            title="I would like my vital essence.",
            description="Someone has taken my vital essence "
            "and I would like it back.",
            agency=agency_ein,
            date_created=date_created,
            date_submitted=date_submitted,
            due_date=get_due_date(date_submitted,
                                  ACKNOWLEDGEMENT_DAYS_DUE),
            submission='Direct Input',
            current_status='Open')
        create_object(self.request)

    def add_file(self,
                 filepath=None,
                 mime_type='text/plain',
                 title=None):
        if filepath is None:
            filename = uuid.uuid4()
            filepath = os.path.join(current_app.config['UPLOAD_DIRECTORY'],
                                    self.request.id,
                                    filename)
        else:
            filename = os.path.basename(filepath)

        # create an empty file if the specified path does not exist
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            open(filepath, 'w').close()

        file = Files(
            name=filename,
            mime_type=mime_type,
            title=title or filename,
            size=os.path.getsize(filepath)
        )
        create_object(file)
        response = Responses(
            request_id=self.request.id,
            type=response_type.FILE,
            date_modified=datetime.utcnow(),
            metadata_id=file.metadata_id,
            privacy="private",
        )
        create_object(response)
        return response

    def add_note(self):
        pass
