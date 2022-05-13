from datetime import datetime

from elasticsearch.helpers import bulk
from flask import current_app
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app import es
from app.constants import ES_DATETIME_FORMAT, request_status
from app.lib.date_utils import utc_to_local, local_to_utc
from app.lib.utils import InvalidUserException
from app.models import Requests, Agencies
from app.search.constants import (
    MAX_RESULT_SIZE,
    ES_DATE_RANGE_FORMAT,
    DT_DATE_RANGE_FORMAT,
    MOCK_EMPTY_ELASTICSEARCH_RESULT,
)


def recreate():
    """
    Recreate elasticsearch indices and request docs.
    """
    delete_index()
    create_index()
    create_docs()


def index_exists():
    """
    Return whether the elasticsearch index exists or not.
    """
    return es.indices.exists(current_app.config["ELASTICSEARCH_INDEX"])


def delete_index():
    """
    Delete all elasticsearch indices, ignoring errors.
    """
    es.indices.delete(index=current_app.config["ELASTICSEARCH_INDEX"], ignore=[400, 404])


def delete_docs():
    """
    Delete all elasticsearch request docs.
    """
    es.indices.refresh(index=current_app.config["ELASTICSEARCH_INDEX"])
    es.delete_by_query(
        index=current_app.config["ELASTICSEARCH_INDEX"],
        body={"query": {"match_all": {}}},
        conflicts="proceed",
        wait_for_completion=True,
        refresh=True,
    )


def create_index():
    """
    Create elasticsearch index with mappings for request docs.
    """
    es.indices.create(
        index=current_app.config["ELASTICSEARCH_INDEX"],
        body={
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "english",
                        "fields": {
                            # for sorting by title
                            "keyword": {"type": "keyword"}
                        },
                    },
                    "description": {"type": "text", "analyzer": "english"},
                    "agency_request_summary": {
                        "type": "text",
                        "analyzer": "english",
                    },
                    "requester_id": {"type": "keyword"},
                    "title_private": {"type": "boolean"},
                    "agency_request_summary_private": {"type": "boolean"},
                    "agency_ein": {"type": "keyword"},
                    "agency_name": {"type": "keyword"},
                    "agency_acronym": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "date_submitted": {
                        "type": "date",
                        "format": "strict_date_hour_minute_second",
                    },
                    "date_due": {
                        "type": "date",
                        "format": "strict_date_hour_minute_second",
                    },
                    "date_created": {
                        "type": "date",
                        "format": "strict_date_hour_minute_second",
                    },
                    "date_received": {
                        "type": "date",
                        "format": "strict_date_hour_minute_second",
                    },
                    "date_closed": {
                        "type": "date",
                        "format": "strict_date_hour_minute_second",
                    },
                    "assigned_users": {"type": "keyword"},
                    "request_type": {"type": "keyword"},
                }
            }
        },
    )


def create_docs():
    """
    Create elasticsearch request docs for every request db record.
    """

    agency_eins = {a.ein: a for a in Agencies.query.filter_by(is_active=True).all()}

    #: :type: collections.Iterable[app.models.Requests]
    requests = (
        Requests.query.filter(Requests.agency_ein.in_(agency_eins.keys()))
        .options(joinedload(Requests.agency_users))
        .options(joinedload(Requests.requester))
        .all()
    )
    operations = []
    for r in requests:
        date_received = (
            r.date_created.strftime(ES_DATETIME_FORMAT)
            if r.date_created < r.date_submitted
            else r.date_submitted.strftime(ES_DATETIME_FORMAT)
        )
        request_type = []
        if r.custom_metadata is not None:
            request_type = [metadata["form_name"] for metadata in r.custom_metadata.values()]
        operation = {
            "_op_type": "create",
            "_id": r.id,
            "title": r.title,
            "description": r.description,
            "agency_request_summary": r.agency_request_summary,
            "requester_name": r.requester.name,
            "requester_id": "{guid}".format(guid=r.requester.guid),
            "title_private": r.privacy["title"],
            "agency_request_summary_private": not r.agency_request_summary_released,
            "date_created": r.date_created.strftime(ES_DATETIME_FORMAT),
            "date_submitted": r.date_submitted.strftime(ES_DATETIME_FORMAT),
            "date_received": date_received,
            "date_due": r.due_date.strftime(ES_DATETIME_FORMAT),
            "submission": r.submission,
            "status": r.status,
            "agency_ein": r.agency_ein,
            "agency_acronym": agency_eins[r.agency_ein].acronym,
            "agency_name": agency_eins[r.agency_ein].name,
            "public_title": "Private" if not r.privacy["title"] else r.title,
            "assigned_users": [
                "{guid}".format(guid=user.guid) for user in r.agency_users
            ],
            "request_type": request_type
            # public_agency_request_summary
        }

        if r.date_closed is not None:
            operation["date_closed"] = r.date_closed.strftime(ES_DATETIME_FORMAT)

        operations.append(operation)
    num_success, _ = bulk(
        es,
        operations,
        index=current_app.config["ELASTICSEARCH_INDEX"],
        chunk_size=current_app.config["ELASTICSEARCH_CHUNK_SIZE"],
        raise_on_error=True,
    )
    current_app.logger.info(
        "Successfully created {num_success} of {total_num} docs.".format(
            num_success=num_success, total_num=len(requests)
        )
    )


def search_requests(
    query,
    foil_id,
    title,
    agency_request_summary,
    description,
    requester_name,
    date_rec_from,
    date_rec_to,
    date_due_from,
    date_due_to,
    date_closed_from,
    date_closed_to,
    agency_ein,
    agency_user_guid,
    request_type,
    open_,
    closed,
    in_progress,
    due_soon,
    overdue,
    start,
    sort_date_received,
    sort_date_due,
    sort_title,
    tz_name,
    size=None,
    by_phrase=False,
    highlight=False,
    for_csv=False,
):
    """
    The arguments of this function match the request parameters
    of the '/search/requests' endpoints.

    All date related params expect strings in the format "mm/dd/yyyy"
    All sort related params expect "desc" or "asc"; other strings ignored

    :param query: string to query for
    :param foil_id: search by request id?
    :param title: search by title?
    :param agency_request_summary: search by agency request summary?
    :param description: search by description?
    :param requester_name: search by requester name?
    :param date_rec_from: date created/submitted from
    :param date_rec_to: date created/submitted to
    :param date_due_from: date due from
    :param date_due_to: date due to
    :param date_closed_from: date closed from
    :param date_closed_to: date closed to
    :param agency_ein: agency ein to filter by
    :param agency_user_guid: user (agency) guid to filter by
    :param request_type: request type to filter by
    :param open_: filter by opened requests?
    :param closed: filter by closed requests?
    :param in_progress: filter by in-progress requests?
    :param due_soon: filter by due-soon requests?
    :param overdue: filter by overdue requests?
    :param size: number of requests per page
    :param start: starting index of request result set
    :param sort_date_received: date created/submitted sort direction
    :param sort_date_due: date due sort direction
    :param sort_title: title sort direction
    :param tz_name: timezone name (e.g. "America/New_York")
    :param by_phrase: use phrase matching instead of full-text?
    :param highlight: return highlights?
        if True, will come at a slight performance cost (in order to
        restrict highlights to public fields, iterating over elasticsearch
        query results is required)
    :param for_csv: search for a csv export
        if True, will not check the maximum value of size against MAX_RESULT_SIZE
    :return: elasticsearch json response with result information

    """
    # clean query trailing/leading whitespace
    if query is not None:
        query = query.strip()

    # return no results if there is nothing to query by
    if query and not any(
        (foil_id, title, agency_request_summary, description, requester_name)
    ):
        return MOCK_EMPTY_ELASTICSEARCH_RESULT

    # if searching by foil-id, strip "FOIL-"
    if foil_id:
        query = query.lstrip("FOIL-").lstrip("foil-")

    # set sort (list of "field:direction" pairs)
    sort = [
        ":".join((field, direction))
        for field, direction in {
            "date_received": sort_date_received,
            "date_due": sort_date_due,
            "title.keyword": sort_title,
        }.items()
        if direction in ("desc", "asc")
    ]

    # if no sort options are selected use date_received desc by default
    if len(sort) == 0:
        sort = ["date_received:desc"]

    # set statuses (list of request statuses)
    if current_user.is_agency:
        statuses = {
            request_status.OPEN: open_,
            request_status.CLOSED: closed,
            request_status.IN_PROGRESS: in_progress,
            request_status.DUE_SOON: due_soon,
            request_status.OVERDUE: overdue,
        }
        statuses = [s for s, b in statuses.items() if b]
    else:
        statuses = []
        if open_:
            # Any request that isn't closed is considered open
            statuses.extend(
                [
                    request_status.OPEN,
                    request_status.IN_PROGRESS,
                    request_status.DUE_SOON,
                    request_status.OVERDUE,
                ]
            )
        if closed:
            statuses.append(request_status.CLOSED)

    # set matching type (full-text or phrase matching)
    match_type = "match_phrase" if by_phrase else "match"

    # set date ranges
    def datestr_local_to_utc(datestr):
        return local_to_utc(
            datetime.strptime(datestr, DT_DATE_RANGE_FORMAT), tz_name
        ).strftime(DT_DATE_RANGE_FORMAT)

    date_ranges = []
    if any(
        (
            date_rec_from,
            date_rec_to,
            date_due_from,
            date_due_to,
            date_closed_from,
            date_closed_to,
        )
    ):
        range_filters = {}
        if date_rec_from or date_rec_to:
            range_filters["date_received"] = {"format": ES_DATE_RANGE_FORMAT}
        if date_due_from or date_due_to:
            range_filters["date_due"] = {"format": ES_DATE_RANGE_FORMAT}
        if date_closed_from or date_closed_to:
            range_filters["date_closed"] = {"format": ES_DATE_RANGE_FORMAT}
        if date_rec_from:
            range_filters["date_received"]["gte"] = datestr_local_to_utc(date_rec_from)
        if date_rec_to:
            range_filters["date_received"]["lt"] = datestr_local_to_utc(date_rec_to)
        if date_due_from:
            range_filters["date_due"]["gte"] = datestr_local_to_utc(date_due_from)
        if date_due_to:
            range_filters["date_due"]["lt"] = datestr_local_to_utc(date_due_to)
        if date_closed_from:
            range_filters["date_closed"]["gte"] = datestr_local_to_utc(date_closed_from)
        if date_closed_to:
            range_filters["date_closed"]["lte"] = datestr_local_to_utc(date_closed_to)
        if date_rec_from or date_rec_to:
            date_ranges.append(
                {"range": {"date_received": range_filters["date_received"]}}
            )
        if date_due_from or date_due_to:
            date_ranges.append({"range": {"date_due": range_filters["date_due"]}})
        if date_closed_from or date_closed_to:
            date_ranges.append({"range": {"date_closed": range_filters["date_closed"]}})

    # generate query dsl body
    query_fields = {
        "title": title,
        "description": description,
        "agency_request_summary": agency_request_summary,
        "requester_name": requester_name,
    }
    dsl_gen = RequestsDSLGenerator(
        query,
        query_fields,
        statuses,
        date_ranges,
        agency_ein,
        agency_user_guid,
        request_type,
        match_type,
    )
    if foil_id:
        dsl = dsl_gen.foil_id()
    else:
        if query:
            if current_user.is_agency:
                dsl = dsl_gen.agency_user()
            elif current_user.is_anonymous:
                dsl = dsl_gen.anonymous_user()
            elif current_user.is_public:
                dsl = dsl_gen.public_user()
            else:
                raise InvalidUserException(current_user)
        else:
            dsl = dsl_gen.queryless()

    # add highlights to dsl
    if highlight:
        highlight_fields = {}
        for name, add in query_fields.items():
            if add:
                highlight_fields[name] = {}
        dsl.update(
            {
                "highlight": {
                    "pre_tags": ['<span class="highlight">'],
                    "post_tags": ["</span>"],
                    "fields": highlight_fields,
                }
            }
        )

    # Calculate result set size
    result_set_size = size if for_csv else min(size, MAX_RESULT_SIZE)

    # search / run query
    if not for_csv:
        results = es.search(
            index=current_app.config["ELASTICSEARCH_INDEX"],
            body=dsl,
            _source=[
                "requester_id",
                "date_submitted",
                "date_due",
                "date_received",
                "date_created",
                "date_closed",
                "status",
                "agency_ein",
                "agency_name",
                "agency_acronym",
                "requester_name",
                "title_private",
                "agency_request_summary_private",
                "public_title",
                "title",
                "agency_request_summary",
                "description",
                "assigned_users",
                "request_type",
            ],
            size=result_set_size,
            from_=start,
            sort=sort,
        )

    else:
        results = es.search(
            index=current_app.config["ELASTICSEARCH_INDEX"],
            scroll="1m",
            body=dsl,
            _source=[
                "requester_id",
                "date_submitted",
                "date_due",
                "date_received",
                "date_created",
                "date_closed",
                "status",
                "agency_ein",
                "agency_name",
                "agency_acronym",
                "requester_name",
                "title_private",
                "agency_request_summary_private",
                "public_title",
                "title",
                "agency_request_summary",
                "description",
                "assigned_users",
                "request_type"
            ],
            size=result_set_size,
            from_=start,
            sort=sort,
        )
        sid = results["_scroll_id"]
        scroll_size = results["hits"]["total"]

        scroll_results = results["hits"]["hits"]

        while scroll_size > 0:
            results = es.scroll(scroll="1m", body={"scroll": "1m", "scroll_id": sid})

            scroll_size = len(results["hits"]["hits"])

            scroll_results += results["hits"]["hits"]

        return scroll_results
    # process highlights
    if highlight and not foil_id:
        _process_highlights(results, dsl_gen.requester_id)

    return results


class RequestsDSLGenerator(object):
    """ Class for generating dicts representing query dsl bodies for searching request docs. """

    def __init__(
        self,
        query,
        query_fields,
        statuses,
        date_ranges,
        agency_ein,
        agency_user_guid,
        request_type,
        match_type,
    ):
        self.__query = query
        self.__query_fields = query_fields
        self.__statuses = statuses
        self.__agency_ein = agency_ein
        self.__match_type = match_type

        self.__default_filters = [{"terms": {"status": statuses}}]
        if date_ranges:
            self.__default_filters += date_ranges
        if agency_ein:
            self.__default_filters.append({"term": {"agency_ein": agency_ein}})
        if agency_user_guid:
            self.__default_filters.append(
                {"term": {"assigned_users": agency_user_guid}}
            )
        if request_type:
            self.__default_filters.append(
                {"term": {"request_type": request_type}}
            )

        self.__filters = []
        self.__conditions = []
        self.requester_id = None

    def foil_id(self):
        self.__filters = [
            {"wildcard": {"_uid": "request#FOIL-*{}*".format(self.__query)}}
        ]
        return self.__must_query

    def agency_user(self):
        for name, use in self.__query_fields.items():
            if use:
                self.__filters = [{self.__match_type: {name: self.__query}}]
                self.__conditions.append(self.__must)
        return self.__should

    def anonymous_user(self):
        if self.__query_fields["title"]:
            self.__filters = [
                {self.__match_type: {"title": self.__query}},
                {"term": {"title_private": False}},
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields["agency_request_summary"]:
            self.__filters = [
                {self.__match_type: {"agency_request_summary": self.__query}},
                {"term": {"agency_request_summary_private": False}},
            ]
            self.__conditions.append(self.__must)
        return self.__should

    def public_user(self):
        self.requester_id = current_user.get_id()
        if self.__query_fields["title"]:
            self.__filters = [
                {self.__match_type: {"title": self.__query}},
                {
                    "bool": {
                        "should": [
                            {"term": {"requester_id": self.requester_id}},
                            {"term": {"title_private": False}},
                        ]
                    }
                },
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields["agency_request_summary"]:
            self.__filters = [
                {self.__match_type: {"agency_request_summary": self.__query}},
                {"term": {"agency_request_summary_private": False}},
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields["description"]:
            self.__filters = [
                {self.__match_type: {"description": self.__query}},
                {"term": {"requester_id": self.requester_id}},
            ]
            self.__conditions.append(self.__must)
        return self.__should

    def queryless(self):
        self.__filters = [{"match_all": {}}]
        return self.__must_query

    @property
    def __must_query(self):
        return {"query": self.__must}

    @property
    def __must(self):
        return {"bool": {"must": self.__get_filters()}}

    @property
    def __should(self):
        return {"query": {"bool": {"should": self.__conditions}}}

    def __get_filters(self):
        return self.__filters + self.__default_filters


def convert_dates(results, dt_format=None, tz_name=None):
    """
    Replace datetime values of requests search results with a
    datetime object or a datetime string in the specified format.
    Dates can also be offset according to the given time zone name.

    :results: elasticsearch json results
    :dt_format: datetime string format
    :tz_name: time zone name
    """
    for hit in results["hits"]["hits"]:
        for field in ("date_submitted", "date_due", "date_received", "date_closed"):
            dt_field = hit["_source"].get(field, None)
            if dt_field is not None and dt_field:
                dt = datetime.strptime(hit["_source"][field], ES_DATETIME_FORMAT)
            else:
                continue
            if tz_name:
                dt = utc_to_local(dt, tz_name)
            hit["_source"][field] = (
                dt.strftime(dt_format) if dt_format is not None else dt
            )


def _process_highlights(results, requester_id=None):
    """
    Remove highlights for private and non-requester fields.
    Used for non-agency users.

    Why this is necessary:
    https://github.com/elastic/elasticsearch/issues/6787

    :param results: elasticsearch json search results
    :param requester_id: id of requester as it is exists in results
    """
    if not current_user.is_agency:
        for hit in results["hits"]["hits"]:
            is_requester = (
                requester_id == hit["_source"]["requester_id"]
                if requester_id
                else False
            )
            if (
                "title" in hit["highlight"]
                and hit["_source"]["title_private"]
                and (current_user.is_anonymous or not is_requester)
            ):
                hit["highlight"].pop("title")
            if (
                "agency_request_summary" in hit["highlight"]
                and hit["_source"]["agency_request_summary_private"]
            ):
                hit["highlight"].pop("agency_request_summary")
            if "description" in hit["highlight"] and not is_requester:
                hit["highlight"].pop("description")
