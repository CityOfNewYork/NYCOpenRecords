DEFAULT_HITS_SIZE = 10

ES_DATE_RANGE_FORMAT = 'MM/dd/yyyy'
DT_DATE_RANGE_FORMAT = '%m/%d/%Y'

MOCK_EMPTY_ELASTICSEARCH_RESULT = {
    "hits": {
        "total": 0,
        "hits": []
    }
}

ALL_RESULTS_CHUNKSIZE = 1000

MAX_RESULT_SIZE = 50