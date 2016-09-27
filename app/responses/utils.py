from app.models import Requests, Responses
from app.db_utils import create_object
from datetime import datetime
import json


def process_response(request_id=None, type=None, response_content=None, privacy='private'):
    if type == 'note':
        content = json.dumps({"note": response_content})
        response = Responses(request_id=request_id, type=type, date_modified=datetime.utcnow(),
                             content=content, privacy=privacy)
        create_object(obj=response)
