import csv
from datetime import datetime
from io import StringIO, BytesIO
import re

from flask import current_app, request, render_template, jsonify
from flask.helpers import send_file
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app.lib.date_utils import utc_to_local
from app.lib.utils import eval_request_bool
from app.models import Requests, Responses, Determinations, ResponseTokens
from app.search import search
from app.search.constants import DEFAULT_HITS_SIZE, ALL_RESULTS_CHUNKSIZE
from app.search.utils import search_requests, convert_dates
from app import sentry


@search.route("/requests", methods=["GET"])
def requests():
    """
    For request parameters, see app.search.utils.search_requests

    All Users can search by:
    - FOIL ID

    Anonymous Users can search by:
    - Title (public only)
    - Agency Request Summary (public only)

    Public Users can search by:
    - Title (public only OR public and private if user is requester)
    - Agency Request Summary (public only)
    - Description (if user is requester)

    Agency Users can search by:
    - Title
    - Agency Request Summary
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
        agency_ein = request.args.get("agency_ein", "")
    except ValueError:
        sentry.captureException()
        agency_ein = None

    try:
        size = int(request.args.get("size", DEFAULT_HITS_SIZE))
    except ValueError:
        sentry.captureException()
        size = DEFAULT_HITS_SIZE

    try:
        start = int(request.args.get("start"), 0)
    except ValueError:
        sentry.captureException()
        start = 0

    query = request.args.get("query")

    # Determine if searching for FOIL ID
    foil_id = eval_request_bool(request.args.get("foil_id")) or re.match(
        r"^(FOIL-|foil-|)\d{4}-\d{3}-\d{5}$", query
    )

    results = search_requests(
        query=query,
        foil_id=foil_id,
        title=eval_request_bool(request.args.get("title")),
        agency_request_summary=eval_request_bool(
            request.args.get("agency_request_summary")
        ),
        description=eval_request_bool(request.args.get("description"))
        if not current_user.is_anonymous
        else False,
        requester_name=eval_request_bool(request.args.get("requester_name"))
        if current_user.is_agency
        else False,
        date_rec_from=request.args.get("date_rec_from"),
        date_rec_to=request.args.get("date_rec_to"),
        date_due_from=request.args.get("date_due_from"),
        date_due_to=request.args.get("date_due_to"),
        date_closed_from=request.args.get("date_closed_from"),
        date_closed_to=request.args.get("date_closed_to"),
        agency_ein=agency_ein,
        agency_user_guid=request.args.get("agency_user"),
        request_type=request.args.get("request_type"),
        open_=eval_request_bool(request.args.get("open")),
        closed=eval_request_bool(request.args.get("closed")),
        in_progress=eval_request_bool(request.args.get("in_progress"))
        if current_user.is_agency
        else False,
        due_soon=eval_request_bool(request.args.get("due_soon"))
        if current_user.is_agency
        else False,
        overdue=eval_request_bool(request.args.get("overdue"))
        if current_user.is_agency
        else False,
        size=size,
        start=start,
        sort_date_received=request.args.get("sort_date_submitted"),
        sort_date_due=request.args.get("sort_date_due"),
        sort_title=request.args.get("sort_title"),
        tz_name=request.args.get("tz_name", current_app.config["APP_TIMEZONE"]),
    )

    # format results
    total = results["hits"]["total"]
    formatted_results = None
    if total != 0:
        convert_dates(results)
        formatted_results = render_template(
            "request/result_row.html",
            requests=results["hits"]["hits"],
            today=datetime.utcnow(),
        )
        # query=query)  # only for testing
    return (
        jsonify(
            {
                "count": len(results["hits"]["hits"]),
                "total": total,
                "results": formatted_results,
            }
        ),
        200,
    )


@search.route("/requests/<doc_type>", methods=["GET"])
def requests_doc(doc_type):
    """
    Converts and sends the a search result-set as a
    file of the specified document type.
    - Filtering on set size is ignored; all results are returned.
    - Currently only supports CSVs.
    - CSV only includes requests belonging to that user's agency

    Document name format: "FOIL_requests_results_<timestamp:MM_DD_YYYY_at_HH_mm_pp>"

    Request parameters are identical to those of /search/requests.

    :param doc_type: document type ('csv' only)
    """
    if current_user.is_agency and doc_type.lower() == "csv":
        try:
            agency_ein = request.args.get("agency_ein", "")
        except ValueError:
            sentry.captureException()
            agency_ein = None

        tz_name = request.args.get("tz_name", current_app.config["APP_TIMEZONE"])

        start = 0
        buffer = StringIO()  # csvwriter cannot accept BytesIO
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "FOIL ID",
                "Agency",
                "Title",
                "Agency Request Summary",
                "Current Status",
                "Date Received",
                "Date Due",
                "Closing Reason",
            ]
        )
        results = search_requests(
            query=request.args.get("query"),
            foil_id=eval_request_bool(request.args.get("foil_id")),
            title=eval_request_bool(request.args.get("title")),
            agency_request_summary=eval_request_bool(
                request.args.get("agency_request_summary")
            ),
            description=eval_request_bool(request.args.get("description"))
            if not current_user.is_anonymous
            else False,
            requester_name=eval_request_bool(request.args.get("requester_name"))
            if current_user.is_agency
            else False,
            date_rec_from=request.args.get("date_rec_from"),
            date_rec_to=request.args.get("date_rec_to"),
            date_due_from=request.args.get("date_due_from"),
            date_due_to=request.args.get("date_due_to"),
            date_closed_from=request.args.get("date_closed_from"),
            date_closed_to=request.args.get("date_closed_to"),
            agency_ein=agency_ein,
            agency_user_guid=request.args.get("agency_user"),
            request_type=request.args.get("request_type"),
            open_=eval_request_bool(request.args.get("open")),
            closed=eval_request_bool(request.args.get("closed")),
            in_progress=eval_request_bool(request.args.get("in_progress"))
            if current_user.is_agency
            else False,
            due_soon=eval_request_bool(request.args.get("due_soon"))
            if current_user.is_agency
            else False,
            overdue=eval_request_bool(request.args.get("overdue"))
            if current_user.is_agency
            else False,
            start=start,
            sort_date_received=request.args.get("sort_date_submitted"),
            sort_date_due=request.args.get("sort_date_due"),
            sort_title=request.args.get("sort_title"),
            tz_name=request.args.get("tz_name", current_app.config["APP_TIMEZONE"]),
            for_csv=True,
        )
        ids = [result["_id"] for result in results]
        all_requests = (
            Requests.query.filter(Requests.id.in_(ids))
            .options(joinedload(Requests.agency_users))
            .options(joinedload(Requests.requester))
            .options(joinedload(Requests.agency))
            .all()
        )
        user_agencies = current_user.get_agencies
        count = 1
        for req in all_requests:
            print(count)
            count += 1
            print(req.id)
            reason = ""
            if req.status == 'Closed':
                response = Responses.query.filter(Responses.request_id == req.id,
                                                  Responses.type == 'determinations').order_by(
                    Responses.date_modified.desc()).first()
                determination = Determinations.query.filter(Determinations.id == response.id).one()
                reason = determination.reason
                if reason is "":
                    reason = "N/A"

            if req.agency_ein in user_agencies:
                writer.writerow(
                    [
                        req.id,
                        req.agency.name,
                        req.title,
                        req.agency_request_summary,
                        req.status,
                        req.date_submitted,
                        req.due_date,
                        reason,
                    ]
                )
        dt = datetime.utcnow()
        timestamp = utc_to_local(dt, tz_name) if tz_name is not None else dt
        return send_file(
            BytesIO(buffer.getvalue().encode("UTF-8")),  # convert to bytes
            attachment_filename="nypd_foil_log.csv",
            as_attachment=True,
        )
    return "", 400
