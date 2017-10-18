#!/usr/bin/env bash

# Download and install Logstash
wget https://artifacts.elastic.co/downloads/logstash/logstash-5.6.2.rpm -P /tmp
rpm -ivh /tmp/logstash-5.6.2.rpm

# Start Logstash
sudo initctl start logstash

# Command to test Logstash
# sudo /usr/share/logstash/bin/logstash --path.settings=/etc/logstash -e 'input { stdin { } } output { stdout {} }'
