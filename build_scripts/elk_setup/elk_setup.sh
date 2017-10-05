#!/usr/bin/env bash

# Install Java
yum -y install java-1.8.0-openjdk

# Download and install Elasticsearch
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.6.2.rpm -P /tmp
rpm -ivh /tmp/elasticsearch-5.6.2.rpm
chkconfig --add elasticsearch

# Configure Elasticsearch
mv /etc/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml.orig
ln -s /vagrant/build_scripts/elk_setup/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml
mkdir -p /data/es_logs
chown -R vagrant:vagrant /data
chmod 777 -R /data
# Add the following lines to /etc/security/limits.conf for max number of threads error
# elasticsearch - nproc 2048
# elasticsearch - nofile 65536
service elasticsearch start

# Download and install Kibana
wget https://artifacts.elastic.co/downloads/kibana/kibana-5.6.2-x86_64.rpm -P /tmp
rpm -ivh /tmp/kibana-5.6.2-x86_64.rpm
chkconfig --add kibana

# Configure Kibana
mv /etc/kibana/kibana.yml /etc/kibana/kibana.ynl.orig
ln -s /vagrant/build_scripts/elk_setup/kibana.yml /etc/kibana/kibana.yml
service kibana start


# Download and install Logstash
wget https://artifacts.elastic.co/downloads/logstash/logstash-5.6.2.rpm -P /tmp
rpm -ivh /tmp/logstash-5.6.2.rpm