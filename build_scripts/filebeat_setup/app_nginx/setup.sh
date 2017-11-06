#!/usr/bin/env bash

# 1. Download and install Filebeat
wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-5.6.2-x86_64.rpm -P /tmp
rpm -ivh /tmp/filebeat-5.6.2-x86_64.rpm

cp /vagrant/build_scripts/filebeat_setup/app_nginx/filebeat.yml /etc/filebeat/

# 2. Get Logstash certificate for SSL communication and place in /data/ssl/
# For Dev, run logstash/setup.sh first to get certificate filebeat_setup directory
cp /vagrant/build_scripts/filebeat_setup/logstash_dev.crt /data/ssl/

# 3. Start Filebeat
/etc/init.d/filebeat start

# Add line to sudoers to allow vagrant user to edit filebeat.yml
# vagrant ALL = (root) NOPASSWD: sudoedit /etc/filebeat/filebeat.yml
