"""


"""
from app.models import Request, Agency
from app.utils import create_object, update_object
from datetime import datetime
from business_calendar import FOLLOWING
from app import calendar


def process_request(title=None, description=None, agency=None, submission=None):
    """

    :param title:
    :param description:
    :param agency:
    :param date_created:
    :param submission:
    :return:
    """
    # 1. Generate the request id
    generate_request_id()

    # 2a. Generate Email Notification Text for Agency
    # 2b. Generate Email Notification Text for Requester

    # 3a. Send Email Notification Text for Agency
    # 3b. Send Email Notification Text for Requester

    # 4a. Calculate Request Submitted Date (Round to next business day)
    date_created = datetime.now()
    date_submitted = get_date_submitted(date_created)

    # 4b. Calculate Request Due Date (month day year but time is always 5PM, 5 Days after submitted date)
    due_date = calc_due_date(date_submitted)

    # 5. Create File object (Response table if applicable)

    # 6. Store File object

    # 7. Create Request object

    # 8. Store Request object

    # 9. Store Events object


def generate_request_id(agency):
    """

    :param agency:
    :return:
    """
    next_request_number = Agency.query.filter_by(ein=agency).first().next_request_number
    update_object(type="agency", field="next_request_number", value=next_request_number + 1)
    request_id = 'FOIL-{}-{}-{}'.format(datetime.now().strftime("%Y"), agency, next_request_number)
    return request_id


def get_date_submitted(date_created):
    """

    :param date_created:
    :return:
    """
    date_submitted = calendar.addbusdays(calendar.adjust(date_created, FOLLOWING), FOLLOWING)
    return date_submitted


def calc_due_date(date_submitted):
    """

    :param date_submitted:
    :return:
    """

    due_date = calendar.addbusdays(calendar.adjust(date_submitted.replace(hour=17, minute=00, second=00), 5), 5)
    return due_date

