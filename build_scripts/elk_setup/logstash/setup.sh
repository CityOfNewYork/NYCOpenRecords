#!/usr/bin/env bash

# Download and install Logstash
wget https://artifacts.elastic.co/downloads/logstash/logstash-5.6.2.rpm -P /tmp
rpm -ivh /tmp/logstash-5.6.2.rpm

ln -s /vagrant/build_scripts/elk_setup/logstash/logstash-nginx-es.conf /etc/logstash/conf.d/logstash-nginx-es.conf

# logstash-filter-geoip offline plugin pack to be provided
# /usr/share/logstash/bin/logstash-plugin install file:///vagrant/logstash-filter-geoip.zip

# Start Logstash
sudo initctl start logstash

# Command to test Logstash
# sudo /usr/share/logstash/bin/logstash --path.settings=/etc/logstash -e 'input { stdin { } } output { stdout {} }'
