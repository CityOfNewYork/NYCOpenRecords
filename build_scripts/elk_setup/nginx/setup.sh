#!/usr/bin/env bash

# Install nginx
yum -y install rh-nginx18-nginx


bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-nginx18/enable\n' > /etc/profile.d/nginx18.sh"
source /etc/profile.d/nginx18.sh

mkdir -p /data/nginx_logs

# Configure nginx
mv /etc/opt/rh/rh-nginx18/nginx/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf.orig
ln -s /vagrant/build_scripts/elk_setup/nginx/nginx_conf/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf

# Setup sudo Access
cp /vagrant/build_scripts/elk_setup/nginx/nginx /etc/sudoers.d/nginx