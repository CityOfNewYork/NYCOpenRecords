#!/usr/bin/env bash
#  _       _   _   _  ___  _   __
# / \ | | | \ | | | \  |  | \ |
# \_  | | |_| |   |_|  |  |_| |_
#   \ | | | | |   |\   |  | | |
# \_/ |_| |_/ |_| | \ _|_ |_/ |__ .sh
#
# Usage
#
#	./subscribe.sh
#
# This script will:
# - Disable the firewall permanently
# - Register the system with your Red Hat Developer account
# - Install the latest updates
#
# You will be prompted for your developer account credentials.
#
# If you are running this at DORIS, make sure your proxy is set.
# See /etc/profile.d/proxy.sh
#
# VARIABLES
RHEL_6="6."
RHEL_7="7."

# ensure running as root
if [ "$(id -u)" != "0" ]; then
  exec sudo "$0" "$@"
fi

subscription-manager register --username $1 --password $2 --name $3 --auto-attach --force
subscription-manager attach

if cat /etc/redhat-release | grep -q $RHEL_7; then
    subscription-manager repos --enable rhel-server-rhscl-7-rpms
    subscription-manager repos --enable rhel-7-server-optional-rpms
elif cat /etc/redhat-release | grep -q $RHEL_6; then
    subscription-manager repos --enable rhel-server-rhscl-6-rpms
    subscription-manager repos --enable rhel-6-server-optional-rpms
fi

yum -y update

printf "\nPlease reboot now:\n\n"
printf "\t$ exit\n"
printf "\t$ vagrant reload\n\n"