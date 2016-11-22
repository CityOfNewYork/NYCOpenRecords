from flask import (
    request,
    jsonify,
    render_template,
)
from flask_login import current_user, login_user
from app import es
from app.search import search
from app.search.constants import (
    INDEX,
    DEFAULT_HITS_SIZE,
)
from app.lib.utils import (
    eval_request_bool,
    InvalidUserException,
)
# TODO: HOW TO DENY ACCESS TO ES PORT FOR ANYTHING BUT APP?


@search.route("/", methods=['GET'])
def test():
    return render_template('search/test.html')


@search.route("/requests", methods=['GET'])
def requests():
    """
    Query string parameters:
    - query:
        what is typed into the search box
    - foil_id: (optional, default: false)
        search by id?
    - title: (optional, default: true)
        search by title?
    - description: (optional, default: true)
        search by description?
    - agency_description: (optional, default: true)
        search by agency description?
    - requester_name: (optional: default: false)

    - date_rec_from: (optional)

    - date_rec_to: (optional)

    - date_due_from: (optional)

    - date_due_to: (optional)

    - agency: (optional)

    - open: (optional, default: True)

    - closed: (optional, default: False)

    - due_soon: (optional, default: True if agency user)

    - overdue: (optional, default: True if agency user)

    - size: (optional, default: 10)
        number of results to return
    - by_phrase: (optional, default: false)
        use phrase matching instead of standard full-text?
    - highlight: (optional, default: false)
        show highlights?
        NOTE: if true, will come at a slight performance cost (in order to
        restrict highlights to public fields, iterating over elasticsearch
        query results is required)


    Anonymous Users can search by:
    - Title (public only)
    - Agency Description (public only)

    Public Users can search by:
    - Title (public only OR public and private if user is requester)
    - Agency Description (public only)
    - Description (if user is requester)

    Agency user can search by:
    - Title
    - Agency Description
    - Description
    - Requester Name

    Only Agency users can filter by:
    - Status, Due Soon
    - Status, Overdue
    - Date Due

    """

    # FOR USER TESTING
    # from app.models import Users
    # user = Users.query.first()
    # login_user(user, force=True)

    query = request.args.get('query')
    if query is not None:
        query = query.strip()

    # if query:  # TODO: no matching on fields if no query, just return all docs
    use_id = eval_request_bool(request.args.get('foil_id'), False)
    use_title = eval_request_bool(request.args.get('title'))
    use_agency_desc = eval_request_bool(request.args.get('agency_description'))
    use_description = (eval_request_bool(request.args.get('description'))
                       if not current_user.is_anonymous
                       else False)
    use_requester_name = (eval_request_bool(request.args.get('requester_name'))
                          if current_user.is_agency
                          else False)
    highlight = eval_request_bool(request.args.get('highlight'), False)

    if not any((use_id, use_title, use_agency_desc, use_description, use_requester_name)):
        # nothing to query on
        return jsonify({}), 200

    # Size
    try:
        size = int(request.args.get('size', DEFAULT_HITS_SIZE))
    except ValueError:
        size = DEFAULT_HITS_SIZE

    # Matching Type
    if request.args.get('by_phrase', False):
        match_type = 'match_phrase'
    else:
        match_type = 'match'  # full-text

    fields = {
        'title': use_title,
        'description': use_description,
        'agency_description': use_agency_desc,
        'requester_name': use_requester_name,
    }

    # TODO: user terms (plural) for status

    es_requester_id = None
    if use_id:
        dsl = {
            'query': {
                'wildcard': {
                    '_uid': 'request#FOIL-*{}*'.format(query)
                }
            }
        }
    else:
        conditions = []
        if current_user.is_agency:
            for name, add in fields.items():
                if add:
                    conditions.append({
                        match_type: {name: query}
                    })
            dsl = {
                'query': {
                    'bool': {
                        'should': conditions
                    }
                }
            }
        elif current_user.is_anonymous:
            if use_title:
                conditions.append({
                    'bool': {
                        'must': [
                            {match_type: {'title': query}},
                            {'term': {'title_private': False}}
                        ]
                    }
                })
            if use_agency_desc:
                conditions.append({
                    'bool': {
                        'must': [
                            {match_type: {'agency_description': query}},
                            {'term': {'agency_description_private': False}}
                        ]
                    }
                })
            dsl = {
                'query': {
                    'bool': {
                        'should': conditions
                    }
                }
            }
        elif current_user.is_public:
            es_requester_id = current_user.get_id()
            if use_title:
                conditions.append({
                    'bool': {
                        'must': [
                            {match_type: {'title': query}},
                            {'bool': {
                                'should': [
                                    {'term': {'requester_id': es_requester_id}},
                                    {'term': {'title_private': False}}
                                ]
                            }}
                        ]
                    }
                })
            if use_agency_desc:
                conditions.append({
                    'bool': {
                        'must': [
                            {match_type: {'agency_description': query}},
                            {'term': {'agency_description_private': False}}
                        ]
                    }
                })
            if use_description:
                conditions.append({
                    'bool': {
                        'must': [
                            {match_type: {'description': query}},
                            {'term': {'requester_id': es_requester_id}}
                        ]
                    }
                })
            dsl = {
                'query': {
                    'bool': {
                        'should': conditions
                    }
                }
            }
        else:
            raise InvalidUserException(current_user)

        # Add highlights
        if highlight:
            highlight_fields = {}
            for name, add in fields.items():
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

    results = es.search(
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
                 'public_title'],
        size=size,
    )

    if highlight and not use_id:
        _process_highlights(results, es_requester_id)

    total = results["hits"]["total"]
    formatted_results = None
    if total != 0:
        formatted_results = render_template("request/result_row.html",
                                            requests=results["hits"]["hits"])

    return jsonify({
        "total": total,
        "results": formatted_results
    }), 200


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
