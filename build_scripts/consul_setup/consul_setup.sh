#!/usr/bin/env bash

# Install Consul binaries
cd /tmp/
wget https://releases.hashicorp.com/consul/1.0.0/consul_1.0.0_linux_amd64.zip
unzip consul_1.0.0_linux_amd64.zip
sudo mv consul /usr/bin/

# Start Consul server with this command after build scripts are finished running
# sudo consul agent -server -bootstrap -data-dir /tmp/consul -bind 10.0.0.5 -ui
