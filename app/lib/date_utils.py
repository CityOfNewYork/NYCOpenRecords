from pytz import timezone
from business_calendar import FOLLOWING
from app import calendar
from app.lib import NYCHolidays
from flask import current_app
from datetime import datetime

DEFAULT_YEARS_HOLIDAY_LIST = 5


def get_following_date(date_created):
    """
    Generates the date submitted for a request.

    :param date_created: date (local) the request was made
    :return: date submitted (local) which is the date_created rounded off to the next business day
    """
    return calendar.addbusdays(date_created, FOLLOWING)


def get_next_business_day():
    """
    Generates the next business day based on the current date
    :return: datetime object with the next business day set to 13:00 PM UTC (09:00 AM EST)
    """
    next_business_day = get_following_date(datetime.utcnow())
    next_business_day = next_business_day.replace(hour=13, minute=00, second=00, microsecond=00)

    return next_business_day


def get_due_date(date_submitted, days_until_due, tz_name):
    """
    Generates the due date for a request.

    :param date_submitted: date submitted (local) which is the date_created rounded off to the next business day
    :param days_until_due: number of business days until a request is due
    :param tz_name: time zone name (e.g. "America/New_York")

    :return: due date (utc) with time set to 22:00 PM (5:00 PM EST)
    """
    return process_due_date(
        local_to_utc(calendar.addbusdays(date_submitted, days_until_due), tz_name)
    )


def process_due_date(due_date):
    """
    Returns the given datetime object with a utc time equivalent to 5:00 PM local time (app).

    :param due_date: unprocessed request due date (local)
    :return: naive datetime object
    """
    # set to app's local time
    date = utc_to_local(due_date, current_app.config['APP_TIMEZONE'])
    # set to 5:00 PM
    date = date.replace(hour=17, minute=00, second=00, microsecond=00)
    # revert to utc and return
    return local_to_utc(date, current_app.config['APP_TIMEZONE'])


def local_to_utc(date, tz_name):
    return date - get_timezone_offset(date, tz_name)


def utc_to_local(date, tz_name):
    return date + get_timezone_offset(date, tz_name)


def get_timezone_offset(date, tz_name):
    return timezone(tz_name).localize(date).utcoffset()


def get_holidays_date_list(year_start, year_end=None):
    """
    Generate a list of holiday dates in the range of specified years (including year_end)

    :param year_start: 4 digit year e.g. 2016
    :param year_end: 4 digit year e.g. 2022

    :return: List of dates formatted as strings ['MM/DD/YYYY']
    """
    if year_end:
        years = [year for year in range(year_start, year_end + 1)]
    else:
        years = year_start
    return [str(date.strftime("%m/%d/%Y")) for date, name in NYCHolidays(years=years).items()]


def get_release_date(initial_date, days_until_release, tz_name):
    release_date = calendar.addbusdays(initial_date, days_until_release)
    return utc_to_local(release_date, tz_name)


def is_business_day(date):
    """
    Determine if the provided date is a business day.
    Args:
        date: local date.

    Returns:
        bool: True if date is a business day.

    """
    return calendar.isbusday(date)
