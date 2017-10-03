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
pip install -U sentry
echo "source /home/vagrant/.virtualenvs/sentry/bin/activate" >> /home/vagrant/.bash_profile

# 5. Create default sentry configuration
sentry init /etc/sentry

# 6. Configure sentry
# Configure database connection and web host IP/port in /etc/sentry/sentry.conf.py
# Configure SMTP Mail connection in /etc/sentry/config.yml
