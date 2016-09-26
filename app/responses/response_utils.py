from app.models import Requests, Responses
from app.db_utils import create_object


def process_response(request_id=None, type=None, date_modified=None, content=None, privacy='private'):
    request_id = Requests.query.filter_by(request_id).first()
    if type=
    response = Responses(request_id=request_id, type=type, content=response_content, privacy=privacy)
    create_object(obj=response)
