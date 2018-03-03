#!/usr/bin/env bash

# 1. Install Consul binaries
# if the path to the Consul binaries were provided as a command line argument, then copy it to /usr/local/bin
# Check if the number of arguments is equal to 2 and that the first argument is '-f'
if [[ $# -eq 2 && "$1" == "-f" ]]; then
    filepath=$2
# otherwise download the Consul binaries from HashiCorp
else
    wget https://releases.hashicorp.com/consul/1.0.0/consul_1.0.0_linux_amd64.zip -P /tmp
    cd /tmp/
    unzip consul_1.0.0_linux_amd64.zip
    filepath=/tmp/consul
fi
mv ${filepath} /usr/local/bin

# 2. Create Consul user and Group
mkdir -p /export/local/
sudo useradd consul -d /export/local/consul

# 3. Create configurations for Consul
mkdir -p /etc/consul.d/{bootstrap,server,client}
chown -R consul:consul /etc/consul.d
mkdir /var/consul
chown consul:consul /var/consul
ln -s /vagrant/build_scripts/consul-vault_setup/consul/config.json /etc/consul.d/bootstrap/config.json

# 4. Setup Consul init.d
cp /vagrant/build_scripts/consul-vault_setup/consul/consul /etc/init.d/consul
chmod 755 /etc/init.d/consul

# 5. Encrypt Consul
mkdir -p /etc/consul.d/ssl/CA
chmod 0700 /etc/consul.d/ssl/CA
cd /etc/consul.d/ssl/CA
echo "000a" > serial
ln -s /vagrant/build_scripts/consul-vault_setup/consul/myca.conf /etc/consul.d/ssl/CA/myca.conf
touch certindex

# 6. Create certificates
openssl req -x509 -newkey rsa:2048 -days 365 -nodes -out ca.cert -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=consul"
openssl req -newkey rsa:2048 -nodes -out consul.csr -keyout consul.key -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=consul"
openssl ca -batch -config myca.conf -notext -in consul.csr -out consul.cert
cp ca.cert consul.key consul.cert /etc/consul.d/ssl

# 7. Start Consul server with this command after build scripts are finished running
# consul agent -config-dir /etc/consul.d/bootstrap