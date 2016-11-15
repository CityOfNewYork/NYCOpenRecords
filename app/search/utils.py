from app import es
from app.models import Requests
from elasticsearch.helpers import bulk
from app.search.constants import INDEX


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
                        }
                    }
                }
            }
        },
        ignore=400
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
            'title_private': r.privacy['title'],
            'agency_description_private': r.privacy['agency_description'],
            'date_submitted': r.date_submitted,
            'date_due': r.due_date,
            'submission': r.submission,
            'status': r.status,
            'requester_id': r.requester.get_id(),
            'public_title': 'Private' if r.privacy['title'] else r.title,
            # public_agency_description
        })

    success, _ = bulk(
        es,
        operations,
        index=INDEX,
        doc_type='request',
        chunk_size=100,
        raise_on_error=True
    )
    print("Actions performed:", success)


def update_docs():
    #: :type: collections.Iterable[app.models.Requests]
    requests = Requests.query.all()
    for r in requests:
        r.es_update()  # TODO: in bulk
