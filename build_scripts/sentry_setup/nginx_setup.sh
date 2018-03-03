#!/usr/bin/env bash

# Install nginx
yum -y install rh-nginx18-nginx

bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-nginx18/enable\n' > /etc/profile.d/nginx18.sh"
source /etc/profile.d/nginx18.sh

# Configure nginx
mv /etc/opt/rh/rh-nginx18/nginx/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf.orig
ln -s /vagrant/build_scripts/sentry_setup/nginx_conf/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf

mkdir -p /data/ssl

openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/sentry_setup/sentry_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/sentry_setup/sentry_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=sentry.dev"
    openssl x509 -in /vagrant/build_scripts/sentry_setup/sentry_dev.crt -out /vagrant/build_scripts/sentry_setup/sentry_dev.pem -outform PEM

mv /vagrant/build_scripts/sentry_setup/sentry_dev.key /data/ssl
chmod 400 /data/ssl/sentry_dev.key
mv /vagrant/build_scripts/sentry_setup/sentry_dev.crt /data/ssl
chmod 400 /data/ssl/sentry_dev.crt
mv /vagrant/build_scripts/sentry_setup/sentry_dev.pem /data/ssl
chmod 400 /data/ssl/sentry_dev.pem

service rh-nginx18-nginx start

# Setup sudo Access
cp /vagrant/build_scripts/sentry_setup/nginx /etc/sudoers.d/nginx
