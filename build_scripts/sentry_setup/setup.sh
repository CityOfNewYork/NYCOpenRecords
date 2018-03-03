#!/usr/bin/env bash

# 1. Install Python 2.7
yum -y install python27

# 2. Setup /etc/profile.d/python27.sh
bash -c "printf '#\!/bin/bash\nsource /opt/rh/python27/enable\n' > /etc/profile.d/python27.sh"

# 3. Install required libraries
yum -y install rh-redis32
yum -y install rh-postgresql95-postgresql-devel
yum -y install python27-python-psycopg2
yum -y install libjpeg-turbo-devel
yum -y install zlib-devel

service rh-redis32-redis start

# 4. Install pip packages
source /opt/rh/python27/enable
mkdir /home/vagrant/.virtualenvs
virtualenv --system-site-packages /home/vagrant/.virtualenvs/sentry
chown -R vagrant:vagrant /home/vagrant
source /home/vagrant/.virtualenvs/sentry/bin/activate
pip install --upgrade pip
pip install -U sentry==8.20.0
echo "source /home/vagrant/.virtualenvs/sentry/bin/activate" >> /home/vagrant/.bash_profile

# 5. Create default sentry configuration
sentry init /etc/sentry

# 6. Configure sentry
mv /etc/sentry/sentry.conf.py /etc/sentry/sentry.conf.py.orig
ln -s /vagrant/build_scripts/sentry_setup/sentry.conf.py /etc/sentry/sentry.conf.py
mv /etc/sentry/config.yml /etc/sentry/config.yml.orig
ln -s /vagrant/build_scripts/sentry_setup/config.yml /etc/sentry/config.yml

# 7. Create Initial Schema
SENTRY_CONF=/etc/sentry sentry upgrade --noinput

# 8. Setup sudo Access
cp /vagrant/build_scripts/sentry_setup/redis /etc/sudoers.d/redis
# Sentry commands:
#
# Start Web Service
# SENTRY_CONF=/etc/sentry sentry run web
#
# Start Background Workers
# SENTRY_CONF=/etc/sentry sentry run worker
#
# Start Cron Process
# SENTRY_CONF=/etc/sentry sentry run cron
#
# Create User
# SENTRY_CONF=/etc/sentry sentry createuser
#