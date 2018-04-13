#!/usr/bin/env bash

#!/bin/bash
DATE=$(date +"%Y-%m-%d")
LOGFILE="/backup/openrecords_backup_log-$DATE.log"

source /opt/rh/rh-postgresql95/enable
export MAIL_SERVER=$MAIL_SERVER
export MAIL_PORT=$MAIL_PORT
/usr/bin/python /vagrant/build_scripts/db_setup/backup.py >> $LOGFILE 2>&1