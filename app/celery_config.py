from celery.schedules import crontab


CELERY_IMPORTS = ['app.jobs']
CELERY_TASK_RESULT_EXPIRES = 30
CELERY_TIMEZONE = 'EST'

CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERYBEAT_SCHEDULE = {
    'update_request_statuses': {
        'task': 'app.jobs.update_request_statuses',
        'schedule': crontab(minute='0', hour='7', day_of_week='1-5'),
    },
    'update_next_request_number': {
        'task': 'app.jobs.update_next_request_number',
        'schedule': crontab(minute='0', hour='0', day_of_month='1', month_of_year='1')
    }
}