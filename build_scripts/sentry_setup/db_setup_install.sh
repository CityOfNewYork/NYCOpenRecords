#!/usr/bin/env bash

# 1. Install Postgres 9.5
yum -y install rh-postgresql95
yum -y install rh-postgresql95-postgresql-contrib

chkconfig rh-postgresql95-postgresql on

# 2. Setup Postgres
# Create data directory for Postgres (store data from Postgres where it's not normally stored)
mkdir -p /data/postgres
chown -R postgres:postgres /data/postgres

cp /vagrant/build_scripts/db_setup/postgres.sh /etc/profile.d/postgres.sh
source /etc/profile.d/postgres.sh

postgresql-setup --initdb

# Setup data directory (move data files into created Postgres data directory)
mv /var/opt/rh/rh-postgresql95/lib/pgsql/data/* /data/postgres/
rm -rf /var/opt/rh/rh-postgresql95/lib/pgsql/data
ln -s /data/postgres /var/opt/rh/rh-postgresql95/lib/pgsql/data
chmod 700 /var/opt/rh/rh-postgresql95/lib/pgsql/data

# Postgres Configuration
mv /data/postgres/postgresql.conf /data/postgres/postgresql.conf.orig
mv /data/postgres/pg_hba.conf /data/postgres/pg_hba.conf.orig
cp -r /vagrant/build_scripts/sentry_setup/postgresql.conf /data/postgres/
cp -r /vagrant/build_scripts/sentry_setup/pg_hba.conf /data/postgres/
chown -R postgres:postgres /data/postgres

# 3. Create postgres key and certificates to enable SSL
openssl req \
       -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/sentry_setup/server.key \
       -x509 -days 365 -out /vagrant/build_scripts/sentry_setup/server.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=sentry.dev"
cp /vagrant/build_scripts/sentry_setup/server.crt /vagrant/build_scripts/sentry_setup/root.crt

mv /vagrant/build_scripts/sentry_setup/root.crt /data/postgres
chmod 400 /data/postgres/root.crt
chown postgres:postgres /data/postgres/root.crt
mv /vagrant/build_scripts/sentry_setup/server.crt /data/postgres
chmod 600 /data/postgres/server.crt
chown postgres:postgres /data/postgres/server.crt
mv /vagrant/build_scripts/sentry_setup/server.key /data/postgres
chmod 600 /data/postgres/server.key
chown postgres:postgres /data/postgres/server.key

# 4. Link Postgres Libraries
ln -s /opt/rh/rh-postgresql95/root/usr/lib64/libpq.so.rh-postgresql95-5 /usr/lib64/libpq.so.rh-postgresql95-5
ln -s /opt/rh/rh-postgresql95/root/usr/lib64/libpq.so.rh-postgresql95-5 /usr/lib/libpq.so.rh-postgresql95-5

# 5. Start Postgres
sudo service rh-postgresql95-postgresql start

# 6. Setup sudo Access
cp /vagrant/build_scripts/sentry_setup/postgresql /etc/sudoers.d/postgresql