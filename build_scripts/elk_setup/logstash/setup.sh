#!/usr/bin/env bash

# Download and install Logstash
wget https://artifacts.elastic.co/downloads/logstash/logstash-5.6.2.rpm -P /tmp
rpm -ivh /tmp/logstash-5.6.2.rpm

ln -s /vagrant/build_scripts/elk_setup/logstash/logstash-nginx-es.conf /etc/logstash/conf.d/logstash-nginx-es.conf

cp /etc/pki/tls/openssl.cnf /tmp/logstash_dev.cnf
sed -i '/^\[ v3_ca \]/a subjectAltName = IP: 10.0.0.4' /tmp/logstash_dev.cnf
openssl req -x509 -batch -nodes -newkey rsa:2048 -keyout /vagrant/build_scripts/elk_setup/logstash/logstash_dev.key -out /vagrant/build_scripts/elk_setup/logstash/logstash_dev.crt -config /tmp/logstash_dev.cnf -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=logstash.dev"

mkdir /data/ssl
mv /vagrant/build_scripts/elk_setup/logstash/logstash_dev.key /data/ssl
chmod 400 /data/ssl/logstash_dev.key
mv /vagrant/build_scripts/elk_setup/logstash/logstash_dev.crt /data/ssl
chmod 400 /data/ssl/logstash_dev.crt
chown -R logstash /data/ssl/logstash_dev.*

# logstash-filter-geoip offline plugin pack to be provided
# /usr/share/logstash/bin/logstash-plugin install file:///vagrant/logstash-filter-geoip.zip

# Start Logstash
sudo initctl start logstash

# Command to test Logstash
# sudo /usr/share/logstash/bin/logstash --path.settings=/etc/logstash -e 'input { stdin { } } output { stdout {} }'
