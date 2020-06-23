from datetime import datetime, timedelta

import tablib
from flask import current_app, url_for, request as flask_request
from sqlalchemy import asc, func, Date, or_
from sqlalchemy.orm import joinedload
from urllib.parse import urljoin

from app import celery, db
from app.constants.event_type import REQ_ACKNOWLEDGED, REQ_CREATED, REQ_CLOSED, REQ_DENIED
from app.constants.response_privacy import PRIVATE, RELEASE_AND_PRIVATE, RELEASE_AND_PUBLIC
from app.constants.request_status import OPEN, IN_PROGRESS, DUE_SOON, OVERDUE, CLOSED
from app.lib.date_utils import local_to_utc, utc_to_local
from app.lib.email_utils import send_email
from app.models import Agencies, Emails, Events, Requests, Responses, Users, Files


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
    agency = Agencies.query.options(joinedload(Agencies.active_users)).options(
        joinedload(Agencies.inactive_users)).filter(Agencies.ein == agency_ein).one()

    agency_users = agency.active_users + agency.inactive_users
    request_list = Requests.query.join(
        Events, Events.request_id == Requests.id
    ).options(
        joinedload(Requests.requester)
    ).add_columns(
        Events.user_guid,
        Events.type
    ).filter(
        Requests.agency_ein == agency_ein,
        Requests.status != CLOSED,
        Events.request_id == Requests.id,
        Events.type.in_((REQ_ACKNOWLEDGED, REQ_CREATED))
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

    acknowledged_requests = {res.Requests.id: {"request": res.Requests, "user_guid": res.user_guid} for res in
                             filter(lambda x: x.type == REQ_ACKNOWLEDGED, request_list)}

    unacknowledged_requests = {res.Requests.id: {"request": res.Requests} for res in
                               filter(lambda
                                          x: x.type == REQ_CREATED and x.Requests.id not in acknowledged_requests.keys(),
                                      request_list)}
    request_id_list = list(acknowledged_requests.keys()) + list(unacknowledged_requests.keys())
    for request_id in sorted(request_id_list):
        ack_user = ''
        was_acknowledged = False
        if acknowledged_requests.get(request_id, None):
            ack_user = [user for user in agency_users if user.guid == acknowledged_requests[request_id]["user_guid"]]
            ack_user = ack_user[0].name if ack_user else ''
            was_acknowledged = True
            request = acknowledged_requests.get(request_id)['request']
        else:
            request = unacknowledged_requests.get(request_id)['request']
        req_date_created_local = utc_to_local(request.date_created, current_app.config['APP_TIMEZONE'])
        if date_from < req_date_created_local < date_to:
            data_from_dates.append((
                request.id,
                was_acknowledged,
                ack_user,
                req_date_created_local.strftime('%m/%d/%Y'),
                utc_to_local(request.due_date, current_app.config['APP_TIMEZONE']).strftime('%m/%d/%Y'),
                request.status,
                request.title,
                request.description,
                request.requester.name,
                request.requester.email,
                request.requester.phone_number,
                request.requester.mailing_address.get('address_one'),
                request.requester.mailing_address.get('address_two'),
                request.requester.mailing_address.get('city'),
                request.requester.mailing_address.get('state'),
                request.requester.mailing_address.get('zip'),
            ))
        all_data.append((
            request.id,
            was_acknowledged,
            ack_user,
            req_date_created_local.strftime('%m/%d/%Y'),
            utc_to_local(request.due_date, current_app.config['APP_TIMEZONE']).strftime('%m/%d/%Y'),
            request.status,
            request.title,
            request.description,
            request.requester.name,
            request.requester.email,
            request.requester.phone_number,
            request.requester.mailing_address.get('address_one'),
            request.requester.mailing_address.get('address_two'),
            request.requester.mailing_address.get('city'),
            request.requester.mailing_address.get('state'),
            request.requester.mailing_address.get('zip'),
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


def generate_request_closing_user_report(agency_ein: str, date_from: str, date_to: str, email_to: list):
    """Generates a report of requests that were closed in a time frame.

    Generates a report of requests in a time frame with the following tabs:
    1) Total number of opened and closed requests.
    2) Total number of closed requests and percentage closed by user.
    3) Total number of requests closed by user per day.
    4) All of the requests created.
    5) All of the requests closed.
    6) All of the requests closed and the user who closed it.

    Args:
        agency_ein: Agency EIN
        date_from: Date to filter from
        date_to: Date to filter to
        email_to: List of recipient emails
    """
    # Convert string dates
    date_from_utc = local_to_utc(datetime.strptime(date_from, '%Y-%m-%d'),
                                 current_app.config['APP_TIMEZONE'])
    date_to_utc = local_to_utc(datetime.strptime(date_to, '%Y-%m-%d'),
                               current_app.config['APP_TIMEZONE'])

    # Query for all requests opened and create Dataset
    total_opened = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.date_created.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
    ).order_by(asc(Requests.date_created)).all()
    total_opened_headers = ('Request ID',
                            'Status',
                            'Date Created',
                            'Due Date')
    total_opened_dataset = tablib.Dataset(*total_opened,
                                          headers=total_opened_headers,
                                          title='opened in month Raw Data')

    # Query for all requests closed and create Dataset
    total_closed = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.date_closed, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.date_closed.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Requests.status == CLOSED,
    ).order_by(asc(Requests.date_created)).all()
    total_closed_headers = ('Request ID',
                            'Status',
                            'Date Created',
                            'Date Closed',
                            'Due Date')
    total_closed_dataset = tablib.Dataset(*total_closed,
                                          headers=total_closed_headers,
                                          title='closed in month Raw Data')

    # Get total number of opened and closed requests and create Dataset
    monthly_totals = [
        [OPEN, len(total_opened)],
        [CLOSED, len(total_closed)],
        ['Total', len(total_opened) + len(total_closed)]
    ]
    monthly_totals_headers = ('Status',
                              'Count')
    monthly_totals_dataset = tablib.Dataset(*monthly_totals,
                                            headers=monthly_totals_headers,
                                            title='Monthly Totals')

    # Query for all requests closed with user who closed and create Dataset
    person_month = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
        func.to_char(Events.timestamp, 'MM/DD/YYYY HH:MI:SS.MS'),
        Users.fullname,
    ).distinct().join(
        Events,
        Users,
    ).filter(
        Events.timestamp.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Events.type.in_((REQ_CLOSED, REQ_DENIED)),
        Requests.status == CLOSED,
        Requests.id == Events.request_id,
        Events.user_guid == Users.guid,
    ).order_by(asc(Requests.id)).all()
    person_month_list = [list(r) for r in person_month]
    for person_month_item in person_month_list:
        person_month_item[4] = person_month_item[4].split(' ', 1)[0]
    person_month_headers = ('Request ID',
                            'Status',
                            'Date Created',
                            'Due Date',
                            'Timestamp',
                            'Closed By')
    person_month_dataset = tablib.Dataset(*person_month_list,
                                          headers=person_month_headers,
                                          title='month closed by person Raw Data')

    # Query for count of requests closed by user
    person_month_count = Users.query.with_entities(
        Users.fullname,
        func.count('*'),
    ).distinct().join(
        Events,
        Requests
    ).filter(
        Events.timestamp.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Events.type.in_((REQ_CLOSED, REQ_DENIED)),
        Requests.status == CLOSED,
        Requests.id == Events.request_id,
        Events.user_guid == Users.guid,
    ).group_by(
        Users.fullname
    ).all()
    # Convert query result (tuple) into list
    person_month_count_list = [list(r) for r in person_month_count]
    # Calculate percentage of requests closed by user over total
    for person_month_count_item in person_month_count_list:
        person_month_count_item.append("{:.0%}".format(person_month_count_item[1] / len(person_month)))
    person_month_percent_headers = ('Closed By',
                                    'Count',
                                    'Percent')
    person_month_closing_percent_dataset = tablib.Dataset(*person_month_count_list,
                                                          headers=person_month_percent_headers,
                                                          title='Monthly Closing by Person')

    # Query for count of requests closed per day by user and create Dataset
    person_day = Requests.query.with_entities(
        func.to_char(Events.timestamp.cast(Date), 'MM/DD/YYYY'),
        Users.fullname,
        func.count('*')
    ).join(
        Users
    ).filter(
        Events.timestamp.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Events.type.in_((REQ_CLOSED, REQ_DENIED)),
        Requests.status == CLOSED,
        Requests.id == Events.request_id,
        Events.user_guid == Users.guid,
    ).group_by(
        Events.timestamp.cast(Date),
        Users.fullname,
    ).order_by(Events.timestamp.cast(Date)).all()
    person_day_headers = ('Date',
                          'Closed By',
                          'Count')
    person_day_dataset = tablib.Dataset(*person_day,
                                        headers=person_day_headers,
                                        title='day closed by person Raw Data')

    # Create Databook from Datasets
    excel_spreadsheet = tablib.Databook((monthly_totals_dataset,
                                         person_month_closing_percent_dataset,
                                         person_day_dataset,
                                         total_opened_dataset,
                                         total_closed_dataset,
                                         person_month_dataset))

    # Email report
    send_email(subject='OpenRecords User Closing Report',
               to=email_to,
               email_content='Report attached',
               attachment=excel_spreadsheet.export('xls'),
               filename='FOIL_user_closing_{}_{}.xls'.format(date_from, date_to),
               mimetype='application/octet-stream')


@celery.task(bind=True, name='app.report.utils.generate_monthly_metrics_report')
def generate_monthly_metrics_report(self, agency_ein: str, date_from: str, date_to: str, email_to: list):
    """Generates a report of monthly metrics about opened and closed requests.

    Generates a report of requests in a time frame with the following tabs:
    1) Metrics:
        - Received for the current month
        - Total remaining open for current month
        - Closed in the current month that were received in the current month
        - Total closed in current month no matter when received
        - Total closed since portal started
        - Total remaining Open/Pending
        - Inquiries for current month
    2) All requests that have been opened in the given month.
    3) All requests that are still open or pending. Excludes all closed requests.
    4) All requests that have been closed in the given month.
    5) All requests that have been closed, since the portal started.
    6) All requests that have been opened and closed in the same given month.
    7) all emails received using the "Contact the Agency" button in the given month.

    Args:
        agency_ein: Agency EIN
        date_from: Date to filter from
        date_to: Date to filter to
        email_to: List of recipient emails
    """
    # Convert string dates
    date_from_utc = local_to_utc(datetime.strptime(date_from, '%Y-%m-%d'),
                                 current_app.config['APP_TIMEZONE'])
    date_to_utc = local_to_utc(datetime.strptime(date_to, '%Y-%m-%d'),
                               current_app.config['APP_TIMEZONE']) + timedelta(days=1)

    # Query for all requests that have been opened in the given month
    opened_in_month = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.date_created.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
    ).order_by(asc(Requests.date_created)).all()
    opened_in_month_headers = ('Request ID',
                               'Status',
                               'Date Created',
                               'Due Date')
    opened_in_month_dataset = tablib.Dataset(*opened_in_month,
                                             headers=opened_in_month_headers,
                                             title='Opened in month')

    # Query for all requests that are still open or pending. Excludes all closed requests.
    remaining_open_or_pending = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.agency_ein == agency_ein,
        Requests.status.in_(
            [OPEN, IN_PROGRESS, DUE_SOON, OVERDUE]
        )
    ).order_by(asc(Requests.date_created)).all()
    remaining_open_or_pending_headers = ('Request ID',
                                         'Status',
                                         'Date Created',
                                         'Due Date')
    remaining_open_or_pending_dataset = tablib.Dataset(*remaining_open_or_pending,
                                                       headers=remaining_open_or_pending_headers,
                                                       title='All remaining Open or Pending')

    # Query for all requests that have been closed in the given month.
    closed_in_month = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.date_closed, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.date_closed.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Requests.status == CLOSED,
    ).order_by(asc(Requests.date_created)).all()
    closed_in_month_headers = ('Request ID',
                               'Status',
                               'Date Created',
                               'Date Closed',
                               'Due Date')
    closed_in_month_dataset = tablib.Dataset(*closed_in_month,
                                             headers=closed_in_month_headers,
                                             title='Closed in month')

    # Query for all requests that have been closed, since the portal started.
    total_closed = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.date_closed, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.agency_ein == agency_ein,
        Requests.status == CLOSED,
    ).order_by(asc(Requests.date_created)).all()
    total_closed_headers = ('Request ID',
                            'Status',
                            'Date Created',
                            'Date Closed',
                            'Due Date')
    total_closed_dataset = tablib.Dataset(*total_closed,
                                          headers=total_closed_headers,
                                          title='All Closed requests')

    # Query for all requests that have been opened and closed in the same given month.
    opened_closed_in_month = Requests.query.with_entities(
        Requests.id,
        Requests.status,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Requests.due_date, 'MM/DD/YYYY'),
    ).filter(
        Requests.date_created.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Requests.status == CLOSED,
    ).order_by(asc(Requests.date_created)).all()
    opened_closed_in_month_headers = ('Request ID',
                                      'Status',
                                      'Date Created',
                                      'Due Date')
    opened_closed_in_month_dataset = tablib.Dataset(*opened_closed_in_month,
                                                    headers=opened_closed_in_month_headers,
                                                    title='Opened then Closed in month')

    # Query for all emails received using the "Contact the Agency" button in the given month.
    contact_agency_emails = Requests.query.with_entities(
        Requests.id,
        func.to_char(Requests.date_created, 'MM/DD/YYYY'),
        func.to_char(Responses.date_modified, 'MM/DD/YYYY'),
        Emails.subject
    ).join(Responses, Responses.request_id == Requests.id).join(Emails, Emails.id == Responses.id).filter(
        Responses.date_modified.between(date_from_utc, date_to_utc),
        Requests.agency_ein == agency_ein,
        Emails.subject.ilike('Inquiry about FOIL%')
    ).order_by(asc(Responses.date_modified)).all()
    contact_agency_emails_headers = ('Request ID',
                                     'Date Created',
                                     'Date Sent',
                                     'Subject')
    contact_agency_emails_dataset = tablib.Dataset(*contact_agency_emails,
                                                   headers=contact_agency_emails_headers,
                                                   title='Contact agency emails received')

    # Metrics tab
    received_current_month = len(opened_in_month)
    total_opened_closed_in_month = len(opened_closed_in_month)
    remaining_open_current_month = received_current_month - total_opened_closed_in_month
    metrics = [
        ('Received for the current month', received_current_month),
        ('Total remaining open from current month', remaining_open_current_month),
        ('Closed in the current month that were received in the current month', total_opened_closed_in_month),
        ('Total closed in current month no matter when received', len(closed_in_month)),
        ('Total closed since portal started', len(total_closed)),
        ('Total remaining Open/Pending', len(remaining_open_or_pending)),
        ('Inquiries for current month', len(contact_agency_emails))
    ]
    metrics_headers = ['Metric', 'Count']
    metrics_dataset = tablib.Dataset(*metrics,
                                     headers=metrics_headers,
                                     title='Metrics')

    # Create Databook from Datasets
    excel_spreadsheet = tablib.Databook((
        metrics_dataset,
        opened_in_month_dataset,
        remaining_open_or_pending_dataset,
        closed_in_month_dataset,
        total_closed_dataset,
        opened_closed_in_month_dataset,
        contact_agency_emails_dataset
    ))

    # Email report
    send_email(subject='OpenRecords Monthly Metrics Report',
               to=email_to,
               email_content='Report attached',
               attachment=excel_spreadsheet.export('xls'),
               filename='FOIL_monthly_metrics_report_{}_{}.xls'.format(date_from, date_to),
               mimetype='application/octet-stream')


def generate_open_data_report(agency_ein: str, date_from: datetime, date_to: datetime):
    """Generates a report of Open Data compliance.

    Generates a report of requests in a time frame with the following tabs:
    1) All request responses that could contain possible data sets.
    2) All requests submitted during that given time frame.

    Args:
        agency_ein: Agency EIN
        date_from: Date to filter from
        date_to: Date to filter to
    """

    # Query for all responses that are possible data sets in the given date range
    possible_data_sets = db.session.query(Requests,
                                          Responses,
                                          Files).join(Responses,
                                                      Requests.id == Responses.request_id).join(Files,
                                                                                                Responses.id == Files.id).with_entities(
        Requests.id,
        func.to_char(Requests.date_submitted, 'MM/DD/YYYY'),
        func.to_char(Requests.date_closed, 'MM/DD/YYYY'),
        Requests.title,
        Requests.description,
        Requests.custom_metadata,
        func.to_char(Responses.date_modified, 'MM/DD/YYYY'),
        Responses.privacy,
        func.to_char(Responses.release_date, 'MM/DD/YYYY'),
        Responses.id).filter(
        Requests.agency_ein == agency_ein,
        Requests.date_submitted.between(date_from, date_to),
        Responses.privacy != PRIVATE,
        or_(Files.name.ilike('%xlsx'),
            Files.name.ilike('%csv'),
            Files.name.ilike('%txt'),
            Files.name.ilike('%xls'),
            Files.name.ilike('%data%'),
            Files.title.ilike('%data%'))).all()

    # Process requests for the spreadsheet
    possible_data_sets_processed = []
    for request in possible_data_sets:
        request = list(request)

        # Change privacy value text
        if request[7] == RELEASE_AND_PRIVATE:
            request[7] = 'Release and Private - Agency and Requester Only'
        elif request[7] == RELEASE_AND_PUBLIC:
            request[7] = 'Public'

        # Check if custom_metadata exists
        if request[5] == {} or request[5] is None:
            # Remove custom_metadata from normal requests
            del request[5]
        else:
            # Process custom metadata
            custom_metadata = request[5]
            custom_metadata_text = ''
            for form_number, form_values in sorted(custom_metadata.items()):
                custom_metadata_text = custom_metadata_text + 'Request Type: ' + form_values['form_name'] + '\n\n'
                for field_number, field_values in sorted(form_values['form_fields'].items()):
                    # Make sure field_value exists otherwise give it a default value
                    field_value = field_values.get('field_value', '')
                    # Truncate field_value to 5000 characters for Excel limitations
                    field_value = field_value[:5000]
                    # Set field_value to empty string if None (used for select multiple empty value)
                    if field_value is None:
                        field_value = ''
                    if isinstance(field_value, list):
                        custom_metadata_text = custom_metadata_text + field_values[
                            'field_name'] + ':\n' + ', '.join(field_values.get('field_value', '')) + '\n\n'
                    else:
                        custom_metadata_text = custom_metadata_text + field_values['field_name'] + ':\n' + field_value + '\n\n'
                custom_metadata_text = custom_metadata_text + '\n'
            # Replace normal request description with processed metadata string
            request[4] = custom_metadata_text
            del request[5]

        # Add URL for response
        response_id = request[8]
        del request[8]
        request.append(urljoin(flask_request.host_url, url_for('response.get_response_content', response_id=response_id)))
        possible_data_sets_processed.append(request)

    # Create "Possible Data Sets" data set
    possible_data_sets_headers = ('Request ID',
                                  'Request - Date Submitted',
                                  'Request - Date Closed',
                                  'Request - Title',
                                  'Request - Description',
                                  'Response - Date Added',
                                  'Privacy / Visibility',
                                  'Response - Publish Date',
                                  'URL')
    possible_data_sets_dataset = tablib.Dataset(*possible_data_sets_processed,
                                                headers=possible_data_sets_headers,
                                                title='Possible Data Sets')

    # Query for all requests submitted in the given date range
    all_requests = Requests.query.with_entities(
        Requests.id,
        func.to_char(Requests.date_submitted, 'MM/DD/YYYY'),
        func.to_char(Requests.date_closed, 'MM/DD/YYYY'),
        Requests.title,
        Requests.description,
        Requests.custom_metadata
    ).filter(
        Requests.date_submitted.between(date_from, date_to),
        Requests.agency_ein == agency_ein,
    ).order_by(asc(Requests.date_submitted)).all()

    # Process requests for the spreadsheet
    all_requests_processed = []
    for request in all_requests:
        request = list(request)

        # Check if custom_metadata exists
        if request[5] == {} or request[5] is None:
            del request[5]
        else:
            # Process custom metadata
            custom_metadata = request[5]
            custom_metadata_text = ''
            for form_number, form_values in sorted(custom_metadata.items()):
                custom_metadata_text = custom_metadata_text + 'Request Type: ' + form_values['form_name'] + '\n\n'
                for field_number, field_values in sorted(form_values['form_fields'].items()):
                    field_value = field_values.get('field_value', '')
                    field_value = field_value[:5000]
                    if field_value is None:
                        field_value = ''
                    if isinstance(field_value, list):
                        custom_metadata_text = custom_metadata_text + field_values[
                            'field_name'] + ':\n' + ', '.join(field_values.get('field_value', '')) + '\n\n'
                    else:
                        custom_metadata_text = custom_metadata_text + field_values['field_name'] + ':\n' + field_value + '\n\n'
                custom_metadata_text = custom_metadata_text + '\n'
            request[4] = custom_metadata_text
            del request[5]

        # Add URL to request
        request.append(urljoin(flask_request.host_url, url_for('request.view', request_id=request[0])))
        all_requests_processed.append(request)

    # Create "All Requests" data set
    all_requests_headers = ('Request ID',
                            'Request - Date Submitted',
                            'Request - Date Closed',
                            'Request - Title',
                            'Request - Description',
                            'URL')
    all_requests_dataset = tablib.Dataset(*all_requests_processed,
                                          headers=all_requests_headers,
                                          title='All Requests')

    # Create Databook from Datasets
    excel_spreadsheet = tablib.Databook((
        possible_data_sets_dataset,
        all_requests_dataset,
    ))

    return excel_spreadsheet.export('xls')
