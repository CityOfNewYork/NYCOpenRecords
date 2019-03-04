import tablib
from sqlalchemy import asc

from app import celery
from app.lib.email_utils import send_email
from app.models import Events, Requests, Users


@celery.task(bind=True, name='app.report.utils.generate_acknowledgment_report')
def generate_acknowledgment_report(self, current_user_guid, date_from, date_to):
    current_user = Users.query.filter_by(guid=current_user_guid).one()
    agency_ein = current_user.default_agency_ein

    request_list = Requests.query.filter(Requests.agency_ein == agency_ein,
                                         Requests.date_created.between(date_from, date_to),
                                         Requests.status != 'Closed').order_by(asc(Requests.id)).all()

    headers = ('Request ID',
               'Acknowledged',
               'Acknowledged By',
               'Date Created',
               'Date Received',
               'Date Due',
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
    excel_data = []
    for r in request_list:
        ack_user = ''
        if r.was_acknowledged:
            ack_user = Events.query.filter(Events.request_id == r.id,
                                           Events.type == 'request_acknowledged').one().user.name

        excel_data.append((
            r.id,
            r.was_acknowledged,
            ack_user,
            r.date_created,
            r.date_submitted,
            r.due_date,
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
    data = tablib.Dataset(*excel_data, headers=headers)

    send_email(subject='OpenRecords Acknowledgment Report',
               to=[current_user.email],
               email_content='Report Done.',
               attachment=data.export('xls'),
               filename='test.xls',
               mimetype='application/octect-stream')
