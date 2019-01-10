from celery.schedules import crontab


CELERY_IMPORTS = ['app.jobs']
CELERY_TASK_RESULT_EXPIRES = 30
CELERY_TIMEZONE = 'UTC'

CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERYBEAT_SCHEDULE = {
    'update_request_statuses': {
        'task': 'app.jobs.update_request_statuses',
        # Every minute
        'schedule': crontab(minute='0', hour='7', day_of_week='1-5'),
    }
}