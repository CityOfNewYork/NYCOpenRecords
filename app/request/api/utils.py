from flask_login import current_user

from app.lib.db_utils import create_object
from app.models import Events


def create_request_info_event(request_id, type_, previous_value, new_value):
    """
    Create and store events object for updating the request information into database.
    :param request_id: request ID
    :param type_: event type
    :param previous_value: previous value
    :param new_value: new value
    """
    event = Events(request_id=request_id,
                   user_guid=current_user.guid,
                   type_=type_,
                   previous_value=previous_value,
                   new_value=new_value)
    create_object(event)