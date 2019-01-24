#!/bin/bash
source ~/.bash_profile
pgrep celery | xargs pkill -f
celery worker -A celery_worker.celery --loglevel=info