from business_calendar import FOLLOWING
from app import calendar
from app.models import Requests


def get_following_date(date_created):
    """
    Generates the date submitted for a request.

    :param date_created: date the request was made
    :return: date submitted which is the date_created rounded off to the next business day
    """
    return calendar.addbusdays(date_created, FOLLOWING)


def get_due_date(date_submitted, days_until_due, hour_due=17, minute_due=0, second_due=0):
    """
    Generates the due date for a request.

    :param date_submitted: date submitted which is the date_created rounded off to the next business day
    :param days_until_due: number of business days until a request is due
    :param hour_due: Hour when the request will be marked as overdue, defaults to 1700 (5 P.M.)
    :param minute_due: Minute when the request will be marked as overdue, defaults to 00 (On the hour)
    :param second_due: Second when the request will be marked as overdue, defaults to 00

    :return: due date which is 5 business days after the date_submitted and time is always 5:00 PM
    """
    calc_due_date = calendar.addbusdays(date_submitted, days_until_due)  # calculates due date
    return calc_due_date.replace(hour=hour_due, minute=minute_due, second=second_due)  # sets time to 5:00 PM


def generate_new_due_date(extension_length, request_id):
    """
    Calculates the new due date starting day after the current due date. Calls get_following_date and get_due_date
    functions in lib.date_utils to calculate.

    :param extension_length: length the due date is being extended by (passed in as a string so we must parse to int)
    :param request_id: FOIL request ID, used to query the current due date

    :return: the new due date of the request
    """
    current_request = Requests.query.filter_by(id=request_id).first()
    current_due_date = current_request.due_date
    calc_due_date = get_following_date(current_due_date)
    new_due_date = get_due_date(calc_due_date, int(extension_length))
    return new_due_date