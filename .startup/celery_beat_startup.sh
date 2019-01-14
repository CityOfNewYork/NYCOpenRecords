#!/bin/bash
source ~/.bash_profile
pgrep celery | xargs pkill -f
celery -A celery_worker.celery beat --loglevel=info