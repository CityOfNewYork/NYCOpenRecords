import csv
from datetime import datetime
from io import StringIO, BytesIO
import re

from flask import (
    current_app,
    request,
    render_template,
    jsonify,
)
from flask.helpers import send_file
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app.lib.date_utils import utc_to_local
from app.lib.utils import eval_request_bool
from app.models import Requests
from app.search import search
from app.search.constants import DEFAULT_HITS_SIZE, ALL_RESULTS_CHUNKSIZE
from app.search.utils import search_requests, convert_dates
from app import sentry


@search.route("/requests", methods=['GET'])
def requests():
    """
    For request parameters, see app.search.utils.search_requests

    All Users can search by:
    - FOIL ID

    Anonymous Users can search by:
    - Title (public only)
    - Agency Description (public only)

    Public Users can search by:
    - Title (public only OR public and private if user is requester)
    - Agency Description (public only)
    - Description (if user is requester)

    Agency Users can search by:
    - Title
    - Agency Description
    - Description
    - Requester Name

    All Users can filter by:
    - Status, Open (anything not Closed if not agency user)
    - Status, Closed
    - Date Submitted
    - Agency

    Only Agency Users can filter by:
    - Status, In Progress
    - Status, Due Soon
    - Status, Overdue
    - Date Due

    """
    try:
        agency_ein = request.args.get('agency_ein', '')
    except ValueError:
        sentry.captureException()
        agency_ein = None

    try:
        size = int(request.args.get('size', DEFAULT_HITS_SIZE))
    except ValueError:
        sentry.captureException()
        size = DEFAULT_HITS_SIZE

    try:
        start = int(request.args.get('start'), 0)
    except ValueError:
        sentry.captureException()
        start = 0

    query = request.args.get('query')

    # Determine if searching for FOIL ID
    foil_id = eval_request_bool(request.args.get('foil_id')) or re.match(r'^(FOIL-|foil-|)\d{4}-\d{3}-\d{5}$', query)

    results = search_requests(
        query,
        foil_id,
        eval_request_bool(request.args.get('title')),
        eval_request_bool(request.args.get('agency_request_summary')),
        eval_request_bool(request.args.get('description')) if not current_user.is_anonymous else False,
        eval_request_bool(request.args.get('requester_name')) if current_user.is_agency else False,
        request.args.get('date_rec_from'),
        request.args.get('date_rec_to'),
        request.args.get('date_due_from'),
        request.args.get('date_due_to'),
        request.args.get('date_closed_from'),
        request.args.get('date_closed_to'),
        agency_ein,
        request.args.get('agency_user'),
        eval_request_bool(request.args.get('open')),
        eval_request_bool(request.args.get('closed')),
        eval_request_bool(request.args.get('in_progress')) if current_user.is_agency else False,
        eval_request_bool(request.args.get('due_soon')) if current_user.is_agency else False,
        eval_request_bool(request.args.get('overdue')) if current_user.is_agency else False,
        size,
        start,
        request.args.get('sort_date_submitted'),
        request.args.get('sort_date_due'),
        request.args.get('sort_title'),
        request.args.get('tz_name', current_app.config['APP_TIMEZONE'])
        # eval_request_bool(request.args.get('by_phrase')),
        # eval_request_bool(request.args.get('highlight')),
    )

    # format results
    total = results["hits"]["total"]
    formatted_results = None
    if total != 0:
        convert_dates(results)
        formatted_results = render_template("request/result_row.html",
                                            requests=results["hits"]["hits"])
        # query=query)  # only for testing
    return jsonify({
        "count": len(results["hits"]["hits"]),
        "total": total,
        "results": formatted_results
    }), 200


@search.route("/requests/<doc_type>", methods=['GET'])
def requests_doc(doc_type):
    """
    Converts and sends the a search result-set as a
    file of the specified document type.
    - Filtering on set size is ignored; all results are returned.
    - Currently only supports CSVs.

    Document name format: "FOIL_requests_results_<timestamp:MM_DD_YYYY_at_HH_mm_pp>"

    Request parameters are identical to those of /search/requests.

    :param doc_type: document type ('csv' only)
    """
    if current_user.is_agency and doc_type.lower() == 'csv':
        try:
            agency_ein = request.args.get('agency_ein', '')
        except ValueError:
            sentry.captureException()
            agency_ein = None

        tz_name = request.args.get('tz_name', current_app.config['APP_TIMEZONE'])

        start = 0
        buffer = StringIO()  # csvwriter cannot accept BytesIO
        writer = csv.writer(buffer)
        writer.writerow(["FOIL ID",
                         "Agency",
                         "Title",
                         "Description",
                         "Agency Description",
                         "Current Status",
                         "Date Created",
                         "Date Received",
                         "Date Due",
                         "Date Closed",
                         "Requester Name",
                         "Requester Email",
                         "Requester Title",
                         "Requester Organization",
                         "Requester Phone Number",
                         "Requester Fax Number",
                         "Requester Address 1",
                         "Requester Address 2",
                         "Requester City",
                         "Requester State",
                         "Requester Zipcode",
                         "Assigned User Emails"])
        while True:
            results = search_requests(
                request.args.get('query'),
                eval_request_bool(request.args.get('foil_id')),
                eval_request_bool(request.args.get('title')),
                eval_request_bool(request.args.get('agency_request_summary')),
                eval_request_bool(request.args.get('description')),
                eval_request_bool(request.args.get('requester_name')),
                request.args.get('date_rec_from'),
                request.args.get('date_rec_to'),
                request.args.get('date_due_from'),
                request.args.get('date_due_to'),
                request.args.get('date_closed_from'),
                request.args.get('date_closed_to'),
                agency_ein,
                request.args.get('agency_user'),
                eval_request_bool(request.args.get('open')),
                eval_request_bool(request.args.get('closed')),
                eval_request_bool(request.args.get('in_progress')),
                eval_request_bool(request.args.get('due_soon')),
                eval_request_bool(request.args.get('overdue')),
                ALL_RESULTS_CHUNKSIZE,
                start,
                request.args.get('sort_date_submitted'),
                request.args.get('sort_date_due'),
                request.args.get('sort_title'),
                tz_name,
                for_csv=True
            )
            total = results["hits"]["total"]
            if total != 0:
                ids = [result["_id"] for result in results["hits"]["hits"]]
                all_requests = Requests.query.filter(Requests.id.in_(ids)).options(
                    joinedload(Requests.agency_users)).options(joinedload(Requests.requester)).options(
                    joinedload(Requests.agency)).all()
                for req in all_requests:
                    writer.writerow([
                        req.id,
                        req.agency.name,
                        req.title,
                        req.description,
                        req.agency_request_summary,
                        req.status,
                        req.date_created,
                        req.date_submitted,
                        req.due_date,
                        req.date_closed,
                        req.requester.name,
                        req.requester.email,
                        req.requester.title,
                        req.requester.organization,
                        req.requester.phone_number,
                        req.requester.fax_number,
                        req.requester.mailing_address.get('address_one'),
                        req.requester.mailing_address.get('address_two'),
                        req.requester.mailing_address.get('city'),
                        req.requester.mailing_address.get('state'),
                        req.requester.mailing_address.get('zip'),
                        ", ".join(u.email for u in req.agency_users)])
            start += ALL_RESULTS_CHUNKSIZE
            if start > total:
                break
        if total != 0:
            dt = datetime.utcnow()
            timestamp = utc_to_local(dt, tz_name) if tz_name is not None else dt
            return send_file(
                BytesIO(buffer.getvalue().encode('UTF-8')),  # convert to bytes
                attachment_filename="FOIL_requests_results_{}.csv".format(
                    timestamp.strftime("%m_%d_%Y_at_%I_%M_%p")),
                as_attachment=True
            )
    return '', 400
