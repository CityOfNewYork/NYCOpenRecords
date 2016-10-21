from app import es
from app.models import Requests
from elasticsearch.helpers import bulk
from app.search.constants import INDEX


def create_all():
    es.indices.create(index=INDEX, ignore=400)

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
            'status': r.current_status,
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


def update_all():
    #: :type: collections.Iterable[app.models.Requests]
    requests = Requests.query.all()
    for r in requests:
        r.es_update()  # TODO: in bulk
