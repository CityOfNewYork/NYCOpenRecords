#!/usr/bin/env bash

wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-5.6.2-x86_64.rpm -P /tmp
rpm -ivh /tmp/filebeat-5.6.2-x86_64.rpm

cp /vagrant/build_scripts/filebeat_setup/nginx/filebeat.yml /etc/filebeat/

/etc/init.d/filebeat start

# Allow vagrant user to edit the file
# vagrant ALL = (root) NOPASSWD: sudoedit /etc/filebeat/filebeat.yml
