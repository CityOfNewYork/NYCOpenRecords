#!/usr/bin/env bash

# 1. Install Consul binaries
cp /vagrant/build_scripts/consul_setup/consul_1.0.0_linux_amd64.zip /tmp/
cd /tmp/
unzip consul_1.0.0_linux_amd64.zip
mv consul /usr/local/bin/

# 2. Create configurations for Consul
mkdir -p /etc/consul.d/bootstrap
mkdir /var/consul
ln -s /vagrant/build_scripts/consul_setup/config.json /etc/consul.d/bootstrap/config.json

# 3. Encrypt Consul
mkdir -p /etc/consul.d/ssl/CA
chmod 0700 /etc/consul.d/ssl/CA
cd /etc/consul.d/ssl/CA
echo "000a" > serial
ln -s /vagrant/build_scripts/consul_setup/myca.conf /etc/consul.d/ssl/CA/myca.conf
touch certindex

# Create certificates
openssl req -x509 -newkey rsa:2048 -days 365 -nodes -out ca.cert -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=consul"
openssl req -newkey rsa:2048 -nodes -out consul.csr -keyout consul.key -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=consul"
openssl ca -batch -config myca.conf -notext -in consul.csr -out consul.cert
cp ca.cert consul.key consul.cert /etc/consul.d/ssl
# ln -s /vagrant/build_scripts/consul_setup/encrypt.json /etc/consul.d/bootstrap/encrypt.json

# 4. Start Consul server with this command after build scripts are finished running
# sudo consul agent -config-dir /etc/consul.d/bootstrap