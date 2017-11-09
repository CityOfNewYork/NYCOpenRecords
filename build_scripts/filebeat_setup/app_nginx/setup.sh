#!/usr/bin/env bash

function usage {
   cat << EOF
Usage: setup.sh -u username -h host

Set's up filebeat with SSL Server-to-Server authentication to the Logstash aggregator.
-u Username: Username for the logstash server
-h Hostname: Hostanme of the logstash server

EOF
   exit 1
}

if [[ $# -ne 4 ]]; then
    usage;
fi

if [[ "$1" != "-u" ]]; then
    usage;
fi

if [[ "$3" != "-h" ]]; then
    usage;
fi

username=$2
hostname=$4

# 1. Create /data/ssl directory
mkdir -p /data/ssl

# 2. Get Logstash certificate for SSL communication and place in /data/ssl/
# For Dev, run logstash/setup.sh first to get certificate filebeat_setup directory
scp ${username}@${hostname}:/vagrant/build_scripts/filebeat_setup/logstash_dev.crt /data/ssl/logstash_dev.crt

# 3. Start Filebeat
sudo /etc/init.d/filebeat start
