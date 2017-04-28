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
    show_users = False
    if agency_ein:
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
                if (current_user.is_agency and current_user.agency.ein == agency_ein) or current_user.is_super:
                    if current_user.is_agency_admin or current_user.is_super:
                        active_users = sorted(
                            [(user.guid, user.name)
                             for user in Agencies.query.filter_by(ein=agency_ein).one().active_users],
                            key=lambda x: x[1])
                    elif current_user.is_agency_active:
                        active_users = [(current_user.guid, current_user.name)]
                    if active_users:
                        active_users.insert(0, ('', ''))
                        show_users = True

    elif user_guid and (current_user.is_agency_active or current_user.is_agency_admin or current_user.is_super):
        ureqs = UserRequests.query.filter(UserRequests.user_guid == user_guid,
                                          UserRequests.auth_user_type.in_(user_type_auth.AGENCY_USER_TYPES)
                                         ).all()

        requests_closed = len([u for u in ureqs if u.request.status == request_status.CLOSED])
        requests_opened = len([u for u in ureqs if u.request.status != request_status.CLOSED])

    return jsonify({"labels": ["Opened", "Closed"],
                    "values": [requests_opened, requests_closed],
                    "active_users": active_users,
                    "show_users": show_users
                    }), 200
