"""
.. module:: report.views.

   :synopsis: Handles the report URL endpoints for the OpenRecords application
"""
from datetime import datetime

from flask import (
    current_app,
    render_template,
    jsonify,
    request
)
from flask_login import current_user, login_required

from app.constants import (
    request_status
)
from app.lib.date_utils import local_to_utc
from app.models import (
    Agencies,
    Requests,
    UserRequests
)
from app.report import report
from app.report.forms import AcknowledgmentForm, ReportFilterForm
from app.report.utils import generate_acknowledgment_report


@report.route('/show', methods=['GET'])
def show_report():
    """
    This function handles the rendering of the reports page

    :return: redirect to reports page
    """
    return render_template('report/reports.html',
                           acknowledgment_form=AcknowledgmentForm(),
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


@report.route('/acknowledgment', methods=['POST'])
@login_required
def acknowledgment():
    form = AcknowledgmentForm()
    if form.validate_on_submit():
        # Only agency administrators can access endpoint
        if not current_user.is_agency_admin:
            return jsonify({
                'error': 'Only Agency Administrators can access this endpoint.'
            }), 403

        date_from = local_to_utc(datetime.strptime(request.form['date_from'], '%m/%d/%Y'),
                                 current_app.config['APP_TIMEZONE'])
        date_to = local_to_utc(datetime.strptime(request.form['date_to'], '%m/%d/%Y'),
                               current_app.config['APP_TIMEZONE'])

        redis_key = "{current_user_guid}-{report_type}-{agency_ein}-{timestamp}".format(
            current_user_guid=current_user.guid, report_type='acknowledgment',
            agency_ein=current_user.default_agency_ein,
            timestamp=datetime.now())
        # generate_acknowledgment_report.apply_async(args=(current_user.guid, date_from, date_to), task_id=redis_key)

        return jsonify(), 200
