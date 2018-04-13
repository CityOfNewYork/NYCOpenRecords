#!/usr/bin/env bash

# 1. Install Vault binaries
# if the path to the Vault binaries were provided as a command line argument, then copy it to /usr/local/bin
# Check if the number of arguments is equal to 2 and that the first argument is '-f'
if [[ $# -eq 2 && "$1" == "-f" ]]; then
    filepath=$2
# otherwise download the Vault binaries from HashiCorp
else
    wget https://releases.hashicorp.com/vault/0.8.3/vault_0.8.3_linux_amd64.zip -P /tmp
    cd /tmp/
    unzip vault_0.8.3_linux_amd64.zip
    filepath=/tmp/vault
fi
mv ${filepath} /usr/local/bin

# 2. Create Consul user and Group
mkdir -p /export/local/
sudo useradd vault -d /export/local/vault


# 3. Create configurations for Vault
mkdir -p /etc/vault.d/ssl
ln -s /vagrant/build_scripts/consul-vault_setup/vault/config.hcl /etc/vault.d/config.hcl
sudo -E setcap cap_ipc_lock=+ep $(readlink -f /usr/local/bin/vault)

# 4. Setup Vault init.d
cp /vagrant/build_scripts/consul-vault_setup/vault/vault /etc/init.d/vault
chmod 755 /etc/init.d/vault

# 6. Setup permissions for vault configuration
chown -R vault:vault /etc/vault.d

# 5. Encrypt Vault
mkdir -p /etc/vault.d/ssl/CA
chmod 0700 /etc/vault.d/ssl/CA
cd /etc/vault.d/ssl/CA
echo "000a" > serial
ln -s /vagrant/build_scripts/consul-vault_setup/vault/vault-ca.conf /etc/vault.d/ssl/CA/vault-ca.conf
touch certindex

# 5.1. Create certificates
openssl req -x509 -newkey rsa:2048 -days 365 -nodes -out ca.cert -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=127.0.0.1"
openssl req -newkey rsa:2048 -nodes -out vault.csr -keyout vault.key -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=127.0.0.1"
openssl ca -batch -config /etc/vault.d/ssl/CA/vault-ca.conf -notext -in vault.csr -out vault.cert
cp ca.cert vault.key vault.cert /etc/vault.d/ssl
sudo chown -R vault:vault /etc/vault.d
chmod 0700 /etc/vault.d/ssl/CA

# 5.2 - Setup CA Trust
sudo update-ca-trust enable
cp /etc/vault.d/ssl/ca.cert /etc/pki/ca-trust/source/anchors/ca.crt
sudo update-ca-trust extract
