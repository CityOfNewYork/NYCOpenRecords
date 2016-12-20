from app.report import report
from flask import (
    render_template,
    request as flask_request,
    jsonify
)
from app.models import Requests
from app.constants import request_status
from app.report.forms import ReportFilterForm


# @report.route('/', methods=['GET'])
# def report():
#     return render_template('main/reports.html',
#                            report_filter_form=ReportFilterForm())

@report.route('/', methods=['GET'])
def report():
    agency_ein = flask_request.args.get('agency')
    if agency_ein:
        requests_closed = len(Requests.query.filter_by(status=request_status.CLOSED, agency_ein=agency_ein).all())
        requests_opened = len(Requests.query.filter_by(agency_ein=agency_ein).all()) - requests_closed

        labels = ["Opened", "Closed"]
        values = [requests_opened, requests_closed]

        return jsonify({"labels": labels,
                        "values": values})
    else:
        requests_closed = len(Requests.query.filter_by(status=request_status.CLOSED).all())
        requests_opened = len(Requests.query.all()) - requests_closed

    labels = ["Opened", "Closed"]
    values = [requests_opened, requests_closed]
    return render_template('main/chart.html',
                           values=values,
                           labels=labels,
                           report_filter_form=ReportFilterForm())
