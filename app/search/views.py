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
    - size: (optional, default: 10) number of results to return

    """
    query = request.args.get('query')
    if query is None:
        return jsonify({}), 422

    size = int(request.args.get('size', 10))

    # TODO: there is a better way
    def request_arg_bool_eval(name, default='True'):
        val = request.args.get(name, default)
        try:
            return eval(val.title())
        except NameError:
            return eval(default)

    use_title = request_arg_bool_eval('title')
    use_agency_desc = request_arg_bool_eval('agency_description')
    use_description = request_arg_bool_eval('description')

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
                'pre_tags': ['<span style="background-color: yellow; text-decoration: underline">'],
                'post_tags': ['</span>'],
                'fields': highlight_fields
            }
        },
        _source=['title', 'description', 'agency_description'],
        size=size,
    )

    return jsonify(result), 200
