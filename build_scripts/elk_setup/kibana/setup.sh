#!/usr/bin/env bash

# Download and install Kibana
wget https://artifacts.elastic.co/downloads/kibana/kibana-5.6.2-x86_64.rpm -P /tmp
rpm -ivh /tmp/kibana-5.6.2-x86_64.rpm
chkconfig --add kibana

# Configure Kibana
mv /etc/kibana/kibana.yml /etc/kibana/kibana.yml.orig
cp /vagrant/build_scripts/elk_setup/kibana/kibana.yml /etc/kibana/kibana.yml

# Fix permissions for Kibana
sudo usermod -a -G kibana vagrant
sudo chown -R root:kibana /etc/kibana

# Create self-signed certs
openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=kibana_elk.dev"
    openssl x509 -in /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.crt -out /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.pem -outform PEM

mkdir -p /data/ssl
mv /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.key /data/ssl
chmod 400 /data/ssl/kibana_elk_dev.key
mv /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.crt /data/ssl
chmod 400 /data/ssl/kibana_elk_dev.crt
mv /vagrant/build_scripts/elk_setup/kibana/kibana_elk_dev.pem /data/ssl
chmod 400 /data/ssl/kibana_elk_dev.pem
chown -R kibana:kibana /data/ssl/kibana_elk_dev.*

# Startup Kibana
service kibana start

# Setup sudo Access
cp /vagrant/build_scripts/elk_setup/kibana/kibana /etc/sudoers.d/kibana