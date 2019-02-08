#!/usr/bin/env bash

source /opt/rh/rh-python35/enable

virtualenv --system-site-packages /home/vagrant/.virtualenvs/openrecords
source /home/vagrant/.virtualenvs/openrecords/bin/activate
pip install -r /vagrant/requirements/common.txt