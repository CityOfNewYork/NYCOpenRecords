#!/usr/bin/env bash

# 1. Install Python 3.5
yum -y install rh-python35

# 2. Install Redis 3.2
yum -y install rh-redis32
sudo chkconfig rh-redis32-redis on

# 3. Setup /etc/profile.d/python.sh
bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-python35/enable\n' > /etc/profile.d/python35.sh"

# 4. Install Postgres Python Package (psycopg2) and Postgres Developer Package
yum -y install rh-postgresql95-postgresql-devel
yum -y install rh-python35-python-psycopg2
yum -y install openssl-devel
yum -y install libffi-devel
yum -y install libjpeg-devel
yum -y install zlib-devel
yum -y install cairo
yum -y install pango
yum -y install gdk-pixbuf2


# 5. Install Developer Tools
yum -y groupinstall "Development Tools"

# 6. Install Required pip Packages
source /opt/rh/rh-python35/enable
pip install virtualenv
mkdir /home/vagrant/.virtualenvs
virtualenv --system-site-packages /home/vagrant/.virtualenvs/openrecords
chown -R vagrant:vagrant /home/vagrant
source /home/vagrant/.virtualenvs/openrecords/bin/activate
pip install -r /vagrant/requirements/common.txt

if [ "$1" -eq development ] || [ "$2" -eq development ]; then
    pip install -r /vagrant/requirements/dev.txt
fi

if [ "$1" -eq rhel ] || [ "$2" -eq rhel ]; then
    pip install -r /vagrant/requirements/rhel.txt
fi

# 7. Install telnet-server
yum -y install telnet-server

# 8. Install telnet
yum -y install telnet

# 9. Automatically Use Virtualenv
echo "source /home/vagrant/.virtualenvs/openrecords/bin/activate" >> /home/vagrant/.bash_profile

# 9. Setup sudo Access
cp /vagrant/build_scripts/app_setup/redis /etc/sudoers.d/redis