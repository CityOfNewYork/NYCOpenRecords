#!python

from time import localtime, strftime
import subprocess
import os
import glob
import smtplib
import sys
from datetime import datetime, timedelta

# change these as appropriate for your platform/environment :
USER = "postgres"
PASS = ""
HOST = "127.0.0.1"

BACKUP_DIR = "/backup/"
dumper = """/opt/rh/rh-postgresql95/root/usr/bin/pg_dump -U %s -h 127.0.0.1 -Z 9 -f %s -F c %s  """

sender = 'openrecords@records.nyc.gov'
receivers = ['openrecords@records.nyc.gov']

email = """From: OpenRecords Backup Report <backup@records.nyc.go>
To: OpenRecords Support Staff <openrecords@records.nyc.gov>
Subject: OpenRecords Backup Report %s

""" % strftime("%Y-%m-%d %H-%M-%S", localtime())


def log(string):
    return str(strftime("%Y-%m-%d %H-%M-%S", localtime()) + ": " + str(string) + "\n")


# Change the value in brackets to keep more/fewer files. time.time() returns seconds since 1970...
# currently set to 2 days ago from when this script starts to run.

# x_days_ago = time.time() - ( 60 * 60 * 24 * 30 )
x_days_ago = datetime.now() - timedelta(days=30)

os.putenv('PGPASSWORD', PASS)

database_list = ['openrecords']

# Delete old backup files first.
for database_name in database_list:
    database_name = database_name.strip()
    if database_name == '':
        continue

    glob_list = glob.glob(BACKUP_DIR + database_name + '*' + '.pgdump')
    for file in glob_list:
        file_info = os.stat(file)
        if datetime.fromtimestamp(file_info.st_mtime) < x_days_ago:
            email += log("Deleting: %s" % file)
            os.unlink(file)
        else:
            email += log("Keeping : %s" % file)

email += log("Backup files older than %s deleted." % (x_days_ago.strftime('%a %b %d %H:%M:%S %Y')))

# Now perform the backup.
for database_name in database_list:
    email += log("dump started for %s" % database_name)
    thetime = str(strftime("%Y-%m-%d_%H-%M"))
    file_name = database_name + '_' + thetime + ".sql.pgdump"
    # Run the pg_dump command to the right directory
    command = dumper % (USER, BACKUP_DIR + file_name, database_name)
    email += log(command)
    subprocess.call(command, shell=True)
    email += log("%s dump finished" % database_name)

email += log("Backup job complete.")

try:
    smtpObj = smtplib.SMTP(os.environ.get('MAIL_SERVER'), os.environ.get('MAIL_PORT'))
    smtpObj.sendmail(sender, receivers, email)
    print("Successfully sent email")
except:
    # TODO: Specify different types of exceptions. Should make it easier to troubleshoot / triage failures.
    e = sys.exc_info()[0]
    print(str(e))
