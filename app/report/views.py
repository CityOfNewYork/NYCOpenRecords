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
    request_status,
    user_type_auth
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
    user_guid = request.args.get('user_guid')
    requests_opened = 0
    requests_closed = 0
    active_users = []
    if agency_ein:
        if agency_ein == 'all':
            requests_closed = len(Requests.query.filter_by(status=request_status.CLOSED).all())
            requests_opened = len(Requests.query.all()) - requests_closed
            active_users = []
        else:
            requests_closed = len(Requests.query.filter_by(status=request_status.CLOSED, agency_ein=agency_ein).all())
            requests_opened = len(Requests.query.filter_by(agency_ein=agency_ein).all()) - requests_closed

            active_users = sorted(
                [(user.guid, user.name)
                 for user in Agencies.query.filter_by(ein=agency_ein).one().active_users],
                key=lambda x: x[1])
            if active_users:
                active_users.insert(0, ('', ''))

    elif user_guid and current_user.is_agency:
        ureqs = UserRequests.query.filter_by(user_guid=user_guid,
                                             auth_user_type=user_type_auth.AGENCY_USER).all()

        requests_closed = len([u for u in ureqs if u.request.status == request_status.CLOSED])
        requests_opened = len([u for u in ureqs if u.request.status != request_status.CLOSED])

    return jsonify({"labels": ["Opened", "Closed"],
                    "values": [requests_opened, requests_closed],
                    "active_users": active_users
                    }), 200
