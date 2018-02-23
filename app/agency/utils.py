from app.lib.utils import eval_request_bool
from app.lib.db_utils import update_object, create_object
from app.models import Agencies, Events
from app.constants.event_type import AGENCY_ACTIVATED


def update_agency_active_status(agency_ein, is_active):
    """
    Update the active status of an agency.
    :param agency_ein: String identifier for agency (4 characters)
    :param is_active: Boolean value for agency active status (True = Active)
    :return: Boolean value (True if successfully changed active status)
    """
    pass