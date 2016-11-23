from app import es
from app.models import Requests
from elasticsearch.helpers import bulk
from app.search.constants import INDEX  # FIXME: move out of search (used in models)


def recreate():
    """ For when you feel lazy. """
    es.indices.delete(INDEX, ignore=[400, 404])
    create_index()
    create_docs()


def create_index():
    es.indices.create(
        index=INDEX,
        body={
            "mappings": {
                "request": {
                    "properties": {
                        "title": {
                            "type": "string",
                            "analyzer": "english"
                        },
                        "description": {
                            "type": "string",
                            "analyzer": "english"
                        },
                        "agency_description": {
                            "type": "string",
                            "analyzer": "english"
                        },
                        "requester_id": {
                            "type": "string",
                            "index": "not_analyzed"
                        },
                        "title_private": {
                            "type": "boolean",
                            "index": "not_analyzed"
                        },
                        "agency_description_private": {
                            "type": "boolean",
                            "index": "not_analyzed"
                        },
                        "agency_ein": {
                            "type": "integer",
                            "index": "not_analyzed"
                        },
                        "agency_name": {
                            "type": "string",
                            "index": "not_analyzed"
                        },
                        "status": {
                            "type": "string",
                            "index": "not_analyzed"
                        },
                    }
                }
            }
        },
    )


def create_docs():
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
            'date_submitted': r.date_submitted,
            'date_due': r.due_date,
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
        index=INDEX,
        doc_type='request',
        chunk_size=100,
        raise_on_error=True
    )
    print("Actions performed:", num_success)


def update_docs():
    #: :type: collections.Iterable[app.models.Requests]
    requests = Requests.query.all()
    for r in requests:
        r.es_update()  # TODO: in bulk, if needed at some point


from datetime import datetime
from flask import jsonify, render_template
from flask_login import current_user
from app.constants import request_status
from app.search.constants import DATETIME_FORMAT
from app.lib.utils import InvalidUserException


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
                    open,
                    closed,
                    in_progress,
                    due_soon,
                    overdue,
                    size,
                    start,
                    sort_date_submitted,
                    sort_date_due,
                    sort_date_title,
                    by_phrase=False,
                    highlight=False):
    if query is not None:
        # clean query trailing/leading whitespace
        query = query.strip()

    # return no results if there is nothing to query by
    if query and not any((foil_id, title, agency_description,
                          description, requester_name)):
        return jsonify({"total": 0}), 200

    # set sort
    sort = {
        k: v for k, v in {
        'date_submitted': sort_date_submitted,
        'date_due': sort_date_due,
        'date_title': sort_date_title}.items() if v in ("desc", "asc")}

    # set statuses
    if current_user.is_agency:
        statuses = {
            request_status.OPEN: open,
            request_status.CLOSED: closed,
            request_status.IN_PROGRESS: in_progress,
            request_status.DUE_SOON: due_soon,
            request_status.OVERDUE: overdue
        }
        statuses = [s for s, b in statuses.items() if b]
    else:
        statuses = []
        if open:
            # Any request that isn't closed is considered open
            statuses.extend([
                request_status.OPEN,
                request_status.IN_PROGRESS,
                request_status.DUE_SOON,
                request_status.OVERDUE
            ])
        if closed:
            statuses.append(request_status.CLOSED)

    # set matching type
    match_type = 'match_phrase' if by_phrase else 'match'

    # set date range
    date_range = None
    if any((date_rec_from, date_rec_to, date_due_from, date_due_to)):
        range_filters = {}
        if date_rec_from or date_rec_to:
            range_filters['date_submitted'] = {'format': 'MM/dd/yyyy'}
        if date_due_from or date_due_to:
            range_filters['date_due'] = {'format': 'MM/dd/yyyy'}
        if date_rec_from:
            range_filters['date_submitted']['gte'] = date_rec_from
        if date_rec_to:
            range_filters['date_submitted']['lte'] = date_rec_to
        if date_due_from:
            range_filters['date_due']['gte'] = date_due_from
        if date_due_to:
            range_filters['date_due']['lte'] = date_due_to
        date_range = {'range': range_filters}

    query_fields = {
        'title': title,
        'description': description,
        'agency_description': agency_description,
        'requester_name': requester_name
    }

    # generate query dsl body
    dsl_gen = RequestsDSLGenerator(query, query_fields, statuses, date_range, agency_ein, match_type)
    if foil_id:
        dsl = dsl_gen.foil_id()
    else:
        if query:
            if current_user.is_agency:
                dsl = dsl_gen.agency()
            elif current_user.is_anonymous:
                dsl = dsl_gen.anonymous()
            elif current_user.is_public:
                dsl = dsl_gen.public()
            else:
                raise InvalidUserException(current_user)
        else:
            dsl = dsl_gen.queryless()

    # add highlights
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

    # search
    results =  es.search(
        index=INDEX,
        doc_type='request',
        body=dsl,
        _source=['requester_id',
                 'date_submitted',
                 'date_due',
                 'status',
                 'agency_ein',
                 'agency_name',
                 'requester_name',
                 'title_private',
                 'agency_description_private',
                 'public_title',
                 'title'],
        size=size,
        from_=start,
        sort=sort,
    )

    # process highlights
    if highlight and not foil_id:
        _process_highlights(results, dsl_gen.requester_id)

    # format results
    total = results["hits"]["total"]
    formatted_results = None
    if total != 0:
        _convert_dates(results)
        formatted_results = render_template("request/result_row.html",
                                            requests=results["hits"]["hits"])
    return jsonify({
        "count": len(results["hits"]["hits"]),
        "total": total,
        "results": formatted_results
    }), 200


class RequestsDSLGenerator(object):

    def __init__(self, query, query_fields, statuses, date_range, agency_ein, match_type):
        self.__query = query,
        self.__query_fields = query_fields
        self.__statuses = statuses
        self.__date_range = date_range
        self.__agency_ein = agency_ein
        self.__match_type = match_type

        self.__default_filters = [{'terms': {'status': statuses}}]
        if date_range:
            self.__default_filters.append(date_range)
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

    def agency(self):
        for name, use in self.__query_fields.items():
            self.__filters = [
                {self.__match_type: {name: self.__query}}
            ]
            self.__conditions.append(self.__must)
        return self.__should

    def anonymous(self):
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

    def public(self):
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


def _convert_dates(results):
    """
    Replace 'date_submitted' and 'date_due' of the request search results
    (with the elasticsearch builtin date format: basic_date) with a
    datetime object.
    """
    for hit in results["hits"]["hits"]:
        for field in ("date_submitted", "date_due"):
            hit["_source"][field] = datetime.strptime(hit["_source"][field], DATETIME_FORMAT)


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
