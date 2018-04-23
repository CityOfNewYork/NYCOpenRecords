#!/usr/bin/env bash

# Install Java
yum -y install java-1.8.0-openjdk

# Download and install Elasticsearch
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.6.2.rpm -P /tmp
rpm -ivh /tmp/elasticsearch-5.6.2.rpm
chkconfig --add elasticsearch

# Configure Elasticsearch
mv /etc/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml.orig
ln -s /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml
mkdir -p /data/es_logs
chown -R vagrant:vagrant /data
chmod 777 -R /data

# Fix for max number of threads error when network.host: 0.0.0.0
bash -c "cat << 'EOF' >> /etc/security/limits.conf
elasticsearch - nproc 2048
elasticsearch - nofile 65536
EOF"

# Create self-signed certs
openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=elasticsearch_elk.dev"
    openssl x509 -in /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.crt -out /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.pem -outform PEM

mkdir -p /data/ssl
mv /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.key /data/ssl
chmod 400 /data/ssl/elasticsearch_elk_dev.key
mv /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.crt /data/ssl
chmod 400 /data/ssl/elasticsearch_elk_dev.crt
mv /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch_elk_dev.pem /data/ssl
chmod 400 /data/ssl/elasticsearch_elk_dev.pem

# Startup ElasticSearch
service elasticsearch start

# Setup sudo Access
cp /vagrant/build_scripts/elk_setup/elasticsearch/elasticsearch /etc/sudoers.d/elasticsearch