from datetime import datetime

import tablib
from flask import current_app
from sqlalchemy import asc

from app import celery
from app.constants.event_type import REQ_ACKNOWLEDGED
from app.constants.request_status import CLOSED
from app.lib.date_utils import utc_to_local
from app.lib.email_utils import send_email
from app.models import Events, Requests, Users


@celery.task(bind=True, name='app.report.utils.generate_acknowledgment_report')
def generate_acknowledgment_report(self, current_user_guid: str, date_from: datetime, date_to: datetime):
    """Celery task that generates the acknowledgment report for the user's agency with the specified date range.

    Args:
        current_user_guid: GUID of the current user
        date_from: Date to filter report from
        date_to: Date to filter report to
    """
    current_user = Users.query.filter_by(guid=current_user_guid).one()
    agency_ein = current_user.default_agency_ein
    request_list = Requests.query.filter(Requests.agency_ein == agency_ein,
                                         Requests.status != CLOSED).order_by(asc(Requests.id)).all()
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
    for r in request_list:
        ack_user = ''
        if r.was_acknowledged:
            ack_user = Events.query.filter(Events.request_id == r.id,
                                           Events.type == REQ_ACKNOWLEDGED).one().user.name
        req_date_created_local = utc_to_local(r.date_created, current_app.config['APP_TIMEZONE'])
        if date_from < req_date_created_local < date_to:
            data_from_dates.append((
                r.id,
                r.was_acknowledged,
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
            r.was_acknowledged,
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
