#!/usr/bin/env bash

source /opt/rh/rh-python35/enable

mkdir /home/vagrant/.virtualenvs
virtualenv --system-site-packages /home/vagrant/.virtualenvs/openrecords
source /home/vagrant/.virtualenvs/openrecords/bin/activate
pip install -U pip
pip install -U setuptools
pip install -r /vagrant/requirements/common.txt

if [[ "$1" -eq development ]] || [[ "$2" -eq development ]]; then
    pip install -r /vagrant/requirements/dev.txt
fi