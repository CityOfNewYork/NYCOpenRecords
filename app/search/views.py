# HOW TO DENY ACCESS TO ES PORT FOR ANYTHING BUT APP?

from flask import request, jsonify, render_template
from flask_login import current_user

from app import es
from app.search import search
from app.search.constants import INDEX


@search.route("/", methods=['GET'])
def test():
    return render_template('search/test.html')


@search.route("/requests", methods=['GET'])
def requests():
    """
    Query string parameters:
    - query: (required) what is typed into the search box
    - title: (optional, default: true) search by title?
    - description: (optional, default: true) search by description?
    - agency_description: (optional, default: true) search by agency description?
    - exact: (optional, default: true) don't use full-text searching?

    """
    query = request.args.get('query')
    if query is None:
        return jsonify({}), 422

    use_title = request.args.get('title', True)
    use_agency_desc = request.args.get('agency_description', True)
    use_description = request.args.get('description', True)

    fields = {
        'title': use_title,
        'description': use_description,
        'agency_description': use_agency_desc
    }

    if request.args.get('exact', False):
        match_type = 'match_phrase'
    else:
        match_type = 'match'  # full-text

    match_fields = []
    highlight_fields = {}
    for name, add in fields.items():
        if add:
            match_fields.append({match_type: {name: query}})
            highlight_fields[name] = {}

    result = es.search(
        index=INDEX,
        doc_type='request',
        body={
            'query': {
                'bool': {
                    'should': match_fields
                }
            },
            'highlight': {
                'fields': highlight_fields
            }
        },
        _source=['title', 'description', 'agency_description'],
        size=10,
    )

    return jsonify(result), 200
