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

# 2. Create configurations for Vault
mkdir -p /etc/vault.d
ln -s /vagrant/build_scripts/consul_setup/config.hcl /etc/vault.d/config.hcl
sudo setcap cap_ipc_lock=+ep $(readlink -f $(which vault))

# 3. Start Vault server with this command after Consul server is started
# vault server -config=/etc/vault.d/config.hcl
# export VAULT_ADDR='http://127.0.0.1:8200'

# 4. Initialize Vault server using:
# vault init > /vagrant/build_scripts/consul_setup/vault_unseal_keys.txt
# NOTE: This command saves the unseal keys and initial root token to a text file

# 5. Unseal Vault by running using:
# vault unseal
# NOTE: this needs to be run 3 times in total, using a different unseal key each time

# 6. Authorize Vault using:
# vault auth <Initial Root Token>

# 7. Test Vault installation by writing a test secret (Optional)
# vault write secret/hello value=world

