"""
.. module:: report.views.

   :synopsis: Handles the report URL endpoints for the OpenRecords application
"""
from app.report import report
from flask import (
    render_template,
    jsonify,
    request
)
from flask_login import current_user
from app.models import (
    Agencies,
    Requests,
    UserRequests
)
from app.constants import (
    request_status
)
from app.report.forms import ReportFilterForm


@report.route('/show', methods=['GET'])
def show_report():
    """
    This function handles the rendering of the reports page

    :return: redirect to reports page
    """
    return render_template('report/reports.html',
                           report_filter_form=ReportFilterForm())


@report.route('/', methods=['GET'])
def get():
    """
    This function handles the retrieval of report data to generate the chart on the frontend.
    Takes in agency_ein or user_guid from the frontend and filters for the number of requests closed and requests
    opened.

    :return: json object({"labels": ["Opened", "Closed"],
                          "values": [150, 135],
                          "active_users": [('', ''), ('o8pj0k', 'John Doe')]}), 200
    """
    agency_ein = request.args.get('agency_ein')
    user_guid = request.args.get('user_guid', '')
    requests_opened = 0
    requests_closed = 0
    active_users = []
    is_visible = False
    results = False
    if agency_ein and user_guid == '':
        if agency_ein == 'all':
            active_requests = Requests.query.with_entities(Requests.status).join(
                Agencies, Requests.agency_ein == Agencies.ein).filter(
                Agencies.is_active).all()
            requests_closed = len([r for r in active_requests if r[0] == request_status.CLOSED])
            requests_opened = len(active_requests) - requests_closed
        else:
            active_requests = Requests.query.with_entities(Requests.status).join(
                Agencies, Requests.agency_ein == Agencies.ein).filter(
                Agencies.ein == agency_ein, Agencies.is_active).all()
            requests_closed = len([r for r in active_requests if r[0] == request_status.CLOSED])
            requests_opened = len(active_requests) - requests_closed
            if not (current_user.is_anonymous or current_user.is_public):
                if (current_user.is_agency and current_user.is_agency_admin(agency_ein)) or current_user.is_super:
                    is_visible = True
                    if current_user.is_agency_admin(agency_ein) or current_user.is_super:
                        active_users = sorted(
                            [(user.guid, user.name)
                             for user in Agencies.query.filter_by(ein=agency_ein).one().active_users],
                            key=lambda x: x[1])
                    elif current_user.is_agency_active(agency_ein):
                        active_users = [(current_user.guid, current_user.name)]
                    if active_users:
                        active_users.insert(0, ('', ''))
                        results = True

    elif user_guid and (current_user.is_agency_active(agency_ein) or
                        current_user.is_agency_admin(agency_ein) or
                        current_user.is_super):
        is_visible = True
        ureqs = UserRequests.query.filter(UserRequests.user_guid == user_guid
                                          ).all()

        requests_closed = len([u for u in ureqs if u.request.status == request_status.CLOSED])
        requests_opened = len([u for u in ureqs if u.request.status != request_status.CLOSED])

    return jsonify({"labels": ["Open", "Closed"],
                    "values": [requests_opened, requests_closed],
                    "active_users": active_users,
                    "is_visible": is_visible,
                    "results": results
                    }), 200


@report.route('/fdny', methods=['GET'])
def fdny():
    from datetime import datetime
    from app.lib.date_utils import local_to_utc, utc_to_local
    from flask import current_app
    from app.models import Events
    from io import StringIO, BytesIO
    import csv
    from flask.helpers import send_file
    from sqlalchemy import asc

    agency_ein = '0057'
    start_date = local_to_utc(datetime(2019, 2, 19, 23, 59, 59, 0), current_app.config['APP_TIMEZONE'])
    end_date = local_to_utc(datetime(2019, 2, 27), current_app.config['APP_TIMEZONE'])

    request_list = Requests.query.filter(Requests.agency_ein == agency_ein,
                                         Requests.date_created.between(start_date, end_date),
                                         Requests.status != 'Closed').order_by(asc(Requests.id)).all()

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Request ID',
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
                     'Zipcode'])

    for r in request_list:
        ack_user = ''
        if r.was_acknowledged:
            ack_user = Events.query.filter(Events.request_id == r.id,
                                           Events.type == 'request_acknowledged').one().user.name

        writer.writerow([
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
        ])
    dt = datetime.utcnow()
    timestamp = utc_to_local(dt, current_app.config['APP_TIMEZONE'])
    return send_file(
        BytesIO(buffer.getvalue().encode('UTF-8')),  # convert to bytes
        attachment_filename="FOIL_acknowledgment_{}.csv".format(
            timestamp.strftime("%m_%d_%Y_at_%I_%M_%p")),
        as_attachment=True
    )
