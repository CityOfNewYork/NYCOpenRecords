#!/usr/bin/env bash

# 6. Create sentry user for postgres
sudo -u postgres /opt/rh/rh-postgresql95/root/usr/bin/createuser -s -e sentry

# 7. Create database
sudo -u postgres /opt/rh/rh-postgresql95/root/usr/bin/createdb -E utf-8 sentry