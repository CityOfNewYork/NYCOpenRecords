import csv
from io import StringIO, BytesIO
from datetime import datetime

from flask import (
    request,
    render_template,
    jsonify,
)
from flask.helpers import send_file
from flask_login import current_user
from app.search import search
from app.search.constants import DEFAULT_HITS_SIZE, ALL_RESULTS_CHUNKSIZE
from app.lib.utils import eval_request_bool
from app.lib.date_utils import get_timezone_offset
from app.search.utils import search_requests, convert_dates
from app.models import Requests


@search.route("/", methods=['GET'])
def test():
    return render_template('search/test.html')


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
    - Date Received
    - Agency

    Only Agency Users can filter by:
    - Status, In Progress
    - Status, Due Soon
    - Status, Overdue
    - Date Due

    """

    from flask_login import login_user
    from app.models import Users
    from app.constants.user_type_auth import PUBLIC_USER_NYC_ID, AGENCY_USER
    user = Users.query.filter_by(auth_user_type=AGENCY_USER).first()
    login_user(user, force=True)

    try:
        agency_ein = int(request.args.get('agency_ein', ''))
    except ValueError:
        agency_ein = None

    try:
        size = int(request.args.get('size', DEFAULT_HITS_SIZE))
    except ValueError:
        size = DEFAULT_HITS_SIZE

    try:
        start = int(request.args.get('start'), 0)
    except ValueError:
        start = 0

    query = request.args.get('query')
    results = search_requests(
        query,
        eval_request_bool(request.args.get('foil_id')),
        eval_request_bool(request.args.get('title')),
        eval_request_bool(request.args.get('agency_description')),
        eval_request_bool(request.args.get('description')) if not current_user.is_anonymous else False,
        eval_request_bool(request.args.get('requester_name')) if current_user.is_agency else False,
        request.args.get('date_rec_from'),
        request.args.get('date_rec_to'),
        request.args.get('date_due_from'),
        request.args.get('date_due_to'),
        agency_ein,
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
        # eval_request_bool(request.args.get('by_phrase')),
        # eval_request_bool(request.args.get('highlight')),
    )

    # format results
    total = results["hits"]["total"]
    formatted_results = None
    if total != 0:
        convert_dates(results)
        formatted_results = render_template("request/result_row.html",
                                            requests=results["hits"]["hits"],
                                            query=query)  # TODO: remove after testing
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

    In addition to the request parameters required for searching,
    a client's time zone name (param: tz_name) may be provided.
    Doing so will offset the timestamp present in the file name and
    in any date-specific result fields.

    :param doc_type: document type ('csv' only)
    """
    if current_user.is_agency and doc_type.lower() == 'csv':
        try:
            agency_ein = int(request.args.get('agency_ein', ''))
        except ValueError:
            agency_ein = None

        tz_name = request.args.get('tz_name')

        start = 0
        buffer = StringIO()  # csvwriter cannot accept BytesIO
        writer = csv.writer(buffer)
        writer.writerow(["FOIL ID",
                         "Agency",
                         "Title",
                         "Description",
                         "Agency Description",
                         "Date Created",
                         "Date Received",
                         "Date Due",
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
                eval_request_bool(request.args.get('agency_description')),
                eval_request_bool(request.args.get('description')),
                eval_request_bool(request.args.get('requester_name')),
                request.args.get('date_rec_from'),
                request.args.get('date_rec_to'),
                request.args.get('date_due_from'),
                request.args.get('date_due_to'),
                agency_ein,
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
            )
            total = results["hits"]["total"]
            if total != 0:
                convert_dates(results, tz_name=tz_name)
                for result in results["hits"]["hits"]:
                    r = Requests.query.filter_by(id=result["_id"]).one()
                    mailing_address = (r.requester.mailing_address
                                       if r.requester.mailing_address is not None
                                       else {})
                    writer.writerow([
                        result["_id"],
                        result["_source"]["agency_name"],
                        result["_source"]["title"],
                        result["_source"]["description"],
                        result["_source"]["agency_description"],
                        result["_source"]["date_created"],
                        result["_source"]["date_submitted"],
                        result["_source"]["date_due"],
                        result["_source"]["requester_name"],
                        r.requester.email,
                        r.requester.title,
                        r.requester.organization,
                        r.requester.phone_number,
                        r.requester.fax_number,
                        mailing_address.get('address_one'),
                        mailing_address.get('address_two'),
                        mailing_address.get('city'),
                        mailing_address.get('state'),
                        mailing_address.get('zip'),
                        ", ".join(u.email for u in r.agency_users)])
            start += ALL_RESULTS_CHUNKSIZE
            if start > total:
                break
        if total != 0:
            dt = datetime.utcnow()
            timestamp = dt + get_timezone_offset(dt, tz_name) if tz_name is not None else dt
            return send_file(
                BytesIO(buffer.getvalue().encode('UTF-8')),  # convert to bytes
                attachment_filename="FOIL_requests_results_{}.csv".format(
                    timestamp.strftime("%m_%d_%Y_at_%I_%M_%p")),
                as_attachment=True
            )
    return '', 400
