from celery.schedules import crontab


CELERY_IMPORTS = ['app.jobs']
CELERY_TASK_RESULT_EXPIRES = 30
CELERY_TIMEZONE = 'EST'

CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']

CELERYBEAT_SCHEDULE = {
    'update_request_statuses': {
        'task': 'app.jobs.update_request_statuses',
        'schedule': crontab(minute='0', hour='7', day_of_week='1-5'),
    }
}
