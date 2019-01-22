#!/bin/bash
source ~/.bash_profile
ps -A -o pid,cmd | grep manage.py | grep -v grep | head -n 1 | awk '{print $1}' | xargs kill -9
python manage.py runserver