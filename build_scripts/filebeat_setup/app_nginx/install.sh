#!/usr/bin/env bash

# 1. Check if the number of arguments is equal to 2 and that the first argument is '-f'
if [[ $# -eq 2 && "$1" == "-f" ]]; then
    filepath=$2
else
    wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-5.6.2-x86_64.rpm -P /tmp
    filepath=/tmp/filebeat-5.6.2-x86_64.rpm
fi

# 2. Install Filebeat
rpm -ivh $filepath

# 3. Configure Filebeat
mv /etc/filebeat/filebeat.yml /etc/filebeat/filebeat.yml.orig
cp /vagrant/build_scripts/filebeat_setup/app_nginx/filebeat.yml /etc/filebeat/

# 2. Add line to sudoers to allow vagrant user to edit filebeat.yml
cp /vagrant/build_scripts/filebeat_setup/app_nginx/filebeat /etc/sudoers.d/filebeat