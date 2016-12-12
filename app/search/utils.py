from datetime import datetime

from flask import current_app
from flask_login import current_user
from elasticsearch.helpers import bulk

from app import es
from app.models import Requests
from app.constants import (
    ES_DATETIME_FORMAT,
    request_status
)
from app.search.constants import (
    DATE_RANGE_FORMAT,
    MOCK_EMPTY_ELASTICSEARCH_RESULT
)
from app.lib.utils import InvalidUserException
from app.lib.date_utils import get_timezone_offset


def recreate():
    """ For when you feel lazy. """
    es.indices.delete(current_app.config["ELASTICSEARCH_INDEX"],
                      ignore=[400, 404])
    create_index()
    create_docs()


def create_index():
    """
    Create elasticsearch index with mappings for request docs.
    """
    es.indices.create(
        index=current_app.config["ELASTICSEARCH_INDEX"],
        body={
            "mappings": {
                "request": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "english",
                            "fields": {
                                # for sorting by title
                                "keyword": {
                                    "type": "keyword",
                                }
                            }
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "english"
                        },
                        "agency_description": {
                            "type": "text",
                            "analyzer": "english"
                        },
                        "requester_id": {
                            "type": "keyword",
                        },
                        "title_private": {
                            "type": "boolean",
                        },
                        "agency_description_private": {
                            "type": "boolean",
                        },
                        "agency_ein": {
                            "type": "integer",
                        },
                        "agency_name": {
                            "type": "keyword",
                        },
                        "status": {
                            "type": "keyword",
                        },
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
                        }
                    }
                }
            }
        },
    )


def create_docs():
    """
    Create elasticsearch request docs for every request stored in our db.
    """
    #: :type: collections.Iterable[app.models.Requests]
    requests = Requests.query.all()

    operations = []
    for r in requests:
        operations.append({
            '_op_type': 'create',
            '_id': r.id,
            'title': r.title,
            'description': r.description,
            'agency_description': r.agency_description,
            'requester_name': r.requester.name,
            'title_private': r.privacy['title'],
            'agency_description_private': r.privacy['agency_description'],
            'date_created': r.date_created.strftime(ES_DATETIME_FORMAT),
            'date_submitted': r.date_submitted.strftime(ES_DATETIME_FORMAT),
            'date_due': r.due_date.strftime(ES_DATETIME_FORMAT),
            'submission': r.submission,
            'status': r.status,
            'requester_id': r.requester.get_id(),
            'agency_ein': r.agency_ein,
            'agency_name': r.agency.name,
            'public_title': 'Private' if r.privacy['title'] else r.title,
            # public_agency_description
        })

    num_success, _ = bulk(
        es,
        operations,
        index=current_app.config["ELASTICSEARCH_INDEX"],
        doc_type='request',
        chunk_size=100,
        raise_on_error=True
    )
    print("Successfully created %s docs." % num_success)


def update_docs():
    #: :type: collections.Iterable[app.models.Requests]
    requests = Requests.query.all()
    for r in requests:
        r.es_update()  # TODO: in bulk, if needed at some point


def search_requests(query,
                    foil_id,
                    title,
                    agency_description,
                    description,
                    requester_name,
                    date_rec_from,
                    date_rec_to,
                    date_due_from,
                    date_due_to,
                    agency_ein,
                    open_,
                    closed,
                    in_progress,
                    due_soon,
                    overdue,
                    size,
                    start,
                    sort_date_submitted,
                    sort_date_due,
                    sort_title,
                    by_phrase=False,
                    highlight=False):
    """
    The arguments of this function match the request parameters
    of the '/search/requests' endpoints.

    All date related params expect strings in the format "mm/dd/yyyy"
    All sort related params expect "desc" or "asc"; other strings ignored

    :param query: string to query for
    :param foil_id: search by request id?
    :param title: search by title?
    :param agency_description: search by agency description?
    :param description: search by description?
    :param requester_name: search by requester name?
    :param date_rec_from: date received/submitted from
    :param date_rec_to: date received/submitted to
    :param date_due_from: date due from
    :param date_due_to: date due to
    :param agency_ein: agency ein to filter by
    :param open_: filter by opened requests?
    :param closed: filter by closed requests?
    :param in_progress: filter by in-progress requests?
    :param due_soon: filter by due-soon requests?
    :param overdue: filter by overdue requests?
    :param size: number of requests per page
    :param start: starting index of request result set
    :param sort_date_submitted: date received/submitted sort direction
    :param sort_date_due: date due sort direction
    :param sort_title: title sort direction
    :param by_phrase: use phrase matching instead of full-text?
    :param highlight: return highlights?
        if True, will come at a slight performance cost (in order to
        restrict highlights to public fields, iterating over elasticsearch
        query results is required)
    :return: elasticsearch json response with result information

    """
    # clean query trailing/leading whitespace
    if query is not None:
        query = query.strip()

    # return no results if there is nothing to query by
    if query and not any((foil_id, title, agency_description,
                          description, requester_name)):
        return MOCK_EMPTY_ELASTICSEARCH_RESULT

    # if searching by foil-id, strip "FOIL-"
    if foil_id:
        query = query.lstrip("FOIL-")

    # set sort (list of "field:direction" pairs)
    sort = [
        ':'.join((field, direction)) for field, direction in {
            'date_submitted': sort_date_submitted,
            'date_due': sort_date_due,
            'title.keyword': sort_title}.items() if direction in ("desc", "asc")]

    # set statuses (list of request statuses)
    if current_user.is_agency:
        statuses = {
            request_status.OPEN: open_,
            request_status.CLOSED: closed,
            request_status.IN_PROGRESS: in_progress,
            request_status.DUE_SOON: due_soon,
            request_status.OVERDUE: overdue
        }
        statuses = [s for s, b in statuses.items() if b]
    else:
        statuses = []
        if open_:
            # Any request that isn't closed is considered open
            statuses.extend([
                request_status.OPEN,
                request_status.IN_PROGRESS,
                request_status.DUE_SOON,
                request_status.OVERDUE
            ])
        if closed:
            statuses.append(request_status.CLOSED)

    # set matching type (full-text or phrase matching)
    match_type = 'match_phrase' if by_phrase else 'match'

    # set date ranges
    date_ranges = []
    if any((date_rec_from, date_rec_to, date_due_from, date_due_to)):
        range_filters = {}
        if date_rec_from or date_rec_to:
            range_filters['date_submitted'] = {'format': DATE_RANGE_FORMAT}
        if date_due_from or date_due_to:
            range_filters['date_due'] = {'format': DATE_RANGE_FORMAT}
        if date_rec_from:
            range_filters['date_submitted']['gte'] = date_rec_from
        if date_rec_to:
            range_filters['date_submitted']['lte'] = date_rec_to
        if date_due_from:
            range_filters['date_due']['gte'] = date_due_from
        if date_due_to:
            range_filters['date_due']['lte'] = date_due_to
        if date_rec_from or date_rec_to:
            date_ranges.append({'range': {'date_submitted': range_filters['date_submitted']}})
        if date_due_from or date_due_to:
            date_ranges.append({'range': {'date_due': range_filters['date_due']}})

    # generate query dsl body
    query_fields = {
        'title': title,
        'description': description,
        'agency_description': agency_description,
        'requester_name': requester_name
    }
    dsl_gen = RequestsDSLGenerator(query, query_fields, statuses, date_ranges, agency_ein, match_type)
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
                'highlight': {
                    'pre_tags': ['<span class="highlight">'],
                    'post_tags': ['</span>'],
                    'fields': highlight_fields
                }
            }
        )

    # search / run query
    results = es.search(
        index=current_app.config["ELASTICSEARCH_INDEX"],
        doc_type='request',
        body=dsl,
        _source=['requester_id',
                 'date_submitted',
                 'date_due',
                 'date_created',
                 'status',
                 'agency_ein',
                 'agency_name',
                 'requester_name',
                 'title_private',
                 'agency_description_private',
                 'public_title',
                 'title',
                 'agency_description',
                 'description'],
        size=size,
        from_=start,
        sort=sort,
    )

    # process highlights
    if highlight and not foil_id:
        _process_highlights(results, dsl_gen.requester_id)

    return results


class RequestsDSLGenerator(object):
    """ Class for generating dicts representing query dsl bodies for searching request docs. """

    def __init__(self, query, query_fields, statuses, date_ranges, agency_ein, match_type):
        self.__query = query
        self.__query_fields = query_fields
        self.__statuses = statuses
        self.__agency_ein = agency_ein
        self.__match_type = match_type

        self.__default_filters = [{'terms': {'status': statuses}}]
        if date_ranges:
            self.__default_filters += date_ranges
        if agency_ein:
            self.__default_filters.append({
                'term': {'agency_ein': agency_ein}
            })

        self.__filters = []
        self.__conditions = []
        self.requester_id = None

    def foil_id(self):
        self.__filters = [{
            'wildcard': {
                '_uid': 'request#FOIL-*{}*'.format(self.__query)
            }
        }]
        return self.__must_query

    def agency_user(self):
        for name, use in self.__query_fields.items():
            if use:
                self.__filters = [
                    {self.__match_type: {name: self.__query}}
                ]
                self.__conditions.append(self.__must)
        return self.__should

    def anonymous_user(self):
        if self.__query_fields['title']:
            self.__filters = [
                {self.__match_type: {'title': self.__query}},
                {'term': {'title_private': False}}
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields['agency_description']:
            self.__filters = [
                {self.__match_type: {'agency_description': self.__query}},
                {'term': {'agency_description_private': False}}
            ]
            self.__conditions.append(self.__must)
        return self.__should

    def public_user(self):
        self.requester_id = current_user.get_id()
        if self.__query_fields['title']:
            self.__filters = [
                {self.__match_type: {'title': self.__query}},
                {'bool': {
                    'should': [
                        {'term': {'requester_id': self.requester_id}},
                        {'term': {'title_private': False}}
                    ]
                }}
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields['agency_description']:
            self.__filters = [
                {self.__match_type: {'agency_description': self.__query}},
                {'term': {'agency_description_private': False}}
            ]
            self.__conditions.append(self.__must)
        if self.__query_fields['description']:
            self.__filters = [
                {self.__match_type: {'description': self.__query}},
                {'term': {'requester_id': self.requester_id}},
            ]
            self.__conditions.append(self.__must)
        return self.__should

    def queryless(self):
        self.__filters = [
            {'match_all': {}},
        ]
        return self.__must_query

    @property
    def __must_query(self):
        return {
            'query': self.__must
        }

    @property
    def __must(self):
        return {
            'bool': {
                'must': self.__get_filters()
            }
        }

    @property
    def __should(self):
        return {
            'query': {
                'bool': {
                    'should': self.__conditions
                }
            }
        }

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
        for field in ("date_submitted", "date_due", "date_created"):
            dt = datetime.strptime(hit["_source"][field], ES_DATETIME_FORMAT)
            if tz_name:
                dt += get_timezone_offset(dt, tz_name)
            hit["_source"][field] = dt.strftime(dt_format) if dt_format is not None else dt


def _process_highlights(results, requester_id=None):
    """
    Removes highlights for private and non-requester fields.
    Used for non-agency users.

    Why this is necessary:
    https://github.com/elastic/elasticsearch/issues/6787

    :param results: elasticsearch json search results
    :param requester_id: id of requester as it is exists in results
    """
    if not current_user.is_agency:
        for hit in results['hits']['hits']:
            is_requester = (requester_id == hit['_source']['requester_id']
                            if requester_id
                            else False)
            if ('title' in hit['highlight']
               and hit['_source']['title_private']
               and (current_user.is_anonymous or not is_requester)):
                hit['highlight'].pop('title')
            if ('agency_description' in hit['highlight']
               and hit['_source']['agency_description_private']):
                hit['highlight'].pop('agency_description')
            if ('description' in hit['highlight']
               and not is_requester):
                hit['highlight'].pop('description')
