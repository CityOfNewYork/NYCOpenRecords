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
yum -y install fontpackages-filesystem
yum -y install liberation-fonts-common
yum -y install liberation-sans-fonts
yum -y install urw-fonts
yum -y install texlive-latex
yum -y install libxml2-devel
yum -y install xmlsec1-devel
yum -y install xmlsec1-openssl-devel
yum -y install libtool-ltdl-devel

# 5. Setup SAML
mkdir -p /vagrant/instance/saml
openssl req \
       -newkey rsa:4096 -nodes -keyout /vagrant/instance/saml/certs/saml.key \
       -x509 -days 365 -out /vagrant/instance/saml/certs/saml.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=saml.openrecords.dev"

# 6. Install Developer Tools
yum -y groupinstall "Development Tools"

# 7. Install Required pip Packages
source /opt/rh/rh-python35/enable
pip install virtualenv
pip install --upgrade pip setuptools

if [[ "$1" -eq development ]] || [[ "$2" -eq development ]]; then
    yum -y install telnet-server
    yum -y install telnet
fi

# 8. Automatically Use Virtualenv
echo "source /home/vagrant/.virtualenvs/openrecords/bin/activate" >> /home/vagrant/.bash_profile

# 9. Setup sudo Access
cp /vagrant/build_scripts/app_setup/redis /etc/sudoers.d/redis

# 10. Setup Flask Instance Folder
mkdir -p /vagrant/instance