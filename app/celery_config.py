import os

from celery.schedules import crontab
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)

imports = ['app.jobs']
result_expires = 30
timezone = 'EST'
CELERY_CLEAR_EXPIRED_SESSION_IDS_INTERVAL = os.environ.get('CELERY_CLEAR_EXPIRED_SESSION_IDS_INTERVAL', '*/1')

accept_content = ['pickle', 'json', 'msgpack', 'yaml']

beat_schedule = {
    # Every weekday at 7AM EST
    'update_request_statuses': {
        'task': 'app.jobs.update_request_statuses',
        'schedule': crontab(minute='0', hour='7', day_of_week='1-5')
        # 'schedule': 60.0
    },
    # Every January 1st
    'update_next_request_number': {
        'task': 'app.jobs.update_next_request_number',
        'schedule': crontab(minute='0', hour='0', day_of_month='1', month_of_year='1')
    },
    # Every X minutes
    'clear_expired_session_ids': {
        'task': 'app.jobs.clear_expired_session_ids',
        'schedule': crontab(minute=CELERY_CLEAR_EXPIRED_SESSION_IDS_INTERVAL)
    }
}
