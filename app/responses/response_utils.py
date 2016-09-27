from app.models import Requests, Responses
from app.db_utils import create_object
from app.constants import RESPONSE_TYPE
from datetime import datetime


def process_response(request_id=None, type=None, date_modified=None, content=None, privacy='private'):
    if type is RESPONSE_TYPE['note']:
        response = Responses(request_id=request_id, type=type, date_modified=datetime.utcnow(),
                             content=response_content, privacy=privacy)
        create_object(obj=response)
