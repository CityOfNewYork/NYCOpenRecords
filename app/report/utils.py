from datetime import datetime

import tablib
from flask import current_app
from sqlalchemy import asc, or_, and_

from sqlalchemy.orm import joinedload

from app import celery, db
from app.constants.event_type import REQ_ACKNOWLEDGED
from app.constants.request_status import CLOSED
from app.constants.user_type_request import AGENCY, REQUESTER
from app.lib.date_utils import utc_to_local
from app.lib.email_utils import send_email
from app.models import Events, Requests, Users, Agencies


# @celery.task(bind=True, name='app.report.utils.generate_acknowledgment_report')
def generate_acknowledgment_report(current_user_guid: str, date_from: datetime, date_to: datetime):
    """Celery task that generates the acknowledgment report for the user's agency with the specified date range.

    Args:
        current_user_guid: GUID of the current user
        date_from: Date to filter report from
        date_to: Date to filter report to
    """
    current_user = Users.query.filter_by(guid=current_user_guid).one()
    agency_ein = current_user.default_agency_ein
    agency = Agencies.query.options(joinedload(Agencies.active_users)).options(
        joinedload(Agencies.inactive_users)).filter(Agencies.ein == agency_ein).one()

    agency_users = agency.active_users + agency.inactive_users
    request_list = Requests.query.join(
        Events, Events.request_id == Requests.id
    ).options(
        joinedload(
            Requests.requester
        )
    ).add_columns(
        Events.user_guid,
        Events.type
    ).filter(
        Requests.agency_ein == agency_ein,
        Requests.status != CLOSED,
        Events.request_id == Requests.id
    ).order_by(asc(Requests.id)).all()

    headers = ('Request ID',
               'Acknowledged',
               'Acknowledged By',
               'Date Created',
               'Due Date',
               'Status',
               'Title',
               'Description',
               'Requester Name',
               'Email',
               'Phone Number',
               'Address 1',
               'Address 2',
               'City',
               'State',
               'Zipcode')
    data_from_dates = []
    all_data = []

    acknowledged_requests = list(filter(lambda x: x.type == REQ_ACKNOWLEDGED, request_list))

    for result in request_list:
        ack_user = ''
        was_acknowledged = False
        if result in acknowledged_requests:
            ack_user = [user for user in agency_users if user.guid == result.user_guid]
            ack_user = ack_user[0].name if ack_user else ''
            was_acknowledged = True
        r = result.Requests
        req_date_created_local = utc_to_local(r.date_created, current_app.config['APP_TIMEZONE'])
        if date_from < req_date_created_local < date_to:
            data_from_dates.append((
                r.id,
                was_acknowledged,
                ack_user,
                req_date_created_local.strftime('%m/%d/%Y'),
                utc_to_local(r.due_date, current_app.config['APP_TIMEZONE']).strftime('%m/%d/%Y'),
                r.status,
                r.title,
                r.description,
                r.requester.name,
                r.requester.email,
                r.requester.phone_number,
                r.requester.mailing_address.get('address_one'),
                r.requester.mailing_address.get('address_two'),
                r.requester.mailing_address.get('city'),
                r.requester.mailing_address.get('state'),
                r.requester.mailing_address.get('zip'),
            ))
        all_data.append((
            r.id,
            was_acknowledged,
            ack_user,
            req_date_created_local.strftime('%m/%d/%Y'),
            utc_to_local(r.due_date, current_app.config['APP_TIMEZONE']).strftime('%m/%d/%Y'),
            r.status,
            r.title,
            r.description,
            r.requester.name,
            r.requester.email,
            r.requester.phone_number,
            r.requester.mailing_address.get('address_one'),
            r.requester.mailing_address.get('address_two'),
            r.requester.mailing_address.get('city'),
            r.requester.mailing_address.get('state'),
            r.requester.mailing_address.get('zip'),
        ))
    date_from_string = date_from.strftime('%Y%m%d')
    date_to_string = date_to.strftime('%Y%m%d')
    dates_dataset = tablib.Dataset(*data_from_dates,
                                   headers=headers,
                                   title='{}_{}'.format(date_from_string, date_to_string))
    all_dataset = tablib.Dataset(*all_data, headers=headers, title='all')
    excel_spreadsheet = tablib.Databook((dates_dataset, all_dataset))
    send_email(subject='OpenRecords Acknowledgment Report',
               to=[current_user.email],
               template='email_templates/email_agency_report_generated',
               agency_user=current_user.name,
               attachment=excel_spreadsheet.export('xls'),
               filename='FOIL_acknowledgments_{}_{}.xls'.format(date_from_string, date_to_string),
               mimetype='application/octect-stream')
