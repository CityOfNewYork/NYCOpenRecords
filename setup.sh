#!/usr/bin/env bash

# setup.sh
# --------
#
# Setup OpenRecords development environment.

# add vagrant box if not added
readonly DEFAULT_BOXPATH="./rhel-6.8_vb-5.1.30"
echo Verifying vagrant box \"rhel-6.8_vb-5.1.30\" added...
vagrant box list | grep rhel-6.8_vb-5.1.30 >/dev/null 2>&1 || {
    echo Box not found.
    read -p "path to box file ($DEFAULT_BOXPATH): " boxpath
    boxpath=${boxpath:-$DEFAULT_BOXPATH}
    if [ -f $boxpath ]; then
        vagrant box add rhel-6.8-5.1.30 $boxpath
    else
        echo $boxpath not found
        exit 1
    fi
}

# install vagrant plugins if not installed
echo Checking vagrant plugins...
plugins=`vagrant plugin list`
echo $plugins | grep vagrant-reload >/dev/null 2>&1 || vagrant plugin install vagrant-reload
echo $plugins | grep vagrant-vbguest >/dev/null 2>&1 || vagrant plugin install vagrant-vbguest
echo $plugins | grep vagrant-triggers >/dev/null 2>&1 || vagrant plugin install vagrant-triggers

# Copy Vagrantfile.example if Vagrantfile not found
if [ ! -f Vagrantfile ]; then
    echo Copying Vagrantfile.example to Vagrantfile
    cp Vagrantfile.example Vagrantfile
    read -n1 -p "Would you like to stop this script and make changes to ./Vagrantfile? [y/n] " stop
    case $stop in
        y|Y) echo; echo "Exiting"; exit 0 ;;
    esac
    echo
fi

# get RedHat credentials from env or stdin
if [ "$RH_USER" -a "$RH_PASS" ]; then
    username=${RH_USER}
    password=${RH_PASS}
else
    echo Enter your RedHat Developer Account credentials
    read -p "username: " username
    read -s -p "password: " password
    echo
fi

# Setup system name for RHEL Subscription Management
if [ "$RHSN_SYSTEM_NAME" ]; then
  rhsn_system_name=$RHSN_SYSTEM_NAME
else
  echo "Enter a unique name to identify this system in the RedHat Subscription Management interface"
  read -p "RHSN Name: " rhsn_system_name
fi

# Choose VMs to start up.
default="default "
sentry="sentry "
elk="elk "

vms=""
echo "Choose the VMs to startup using this script (enter y to start the vm)"
read -n1 -p "Default Machine: " vm
case $vm in
    y|Y) echo; vms+=${default}
esac
read -n1 -p "Sentry Machine: " vm
case $vm in
    y|Y) echo; vms+=${sentry}
esac
read -n1 -p "ELK Machine: " vm
case $vm in
    y|Y) echo; vms+=${elk}
esac

echo ${vms}

# vagrant up with RedHat credentials as environment variables
RH_USER=${username} RH_PASSWORD=${password} RHSN_SYSTEM_NAME=${rhsn_system_name} vagrant up ${vms}
