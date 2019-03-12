#!/usr/bin/env bash

# 1. Install Java
yum -y install java-1.8.0-openjdk

# 2. Download Elastic Search
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-6.6.0.rpm -P /tmp

# 3. Install Elastic Search
rpm -ivh /tmp/elasticsearch-6.6.0.rpm

# 4. Autostart Elastic Search
sudo chkconfig --add elasticsearch

# 5. Install nginx and create ssl certs if not running on a single server
if [ "$1" != single_server ]; then
    echo "complete complete complete COMPLETE"
    yum -y install rh-nginx18-nginx

    bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-nginx18/enable\n' > /etc/profile.d/nginx18.sh"

    mv /etc/opt/rh/rh-nginx18/nginx/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf.orig

    ln -s /vagrant/build_scripts/es_setup/nginx_conf/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf

    openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/es_setup/elasticsearch_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=openrecords"
    openssl x509 -in /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -out /vagrant/build_scripts/es_setup/elasticsearch_dev.pem -outform PEM

    sudo service rh-nginx18-nginx restart
fi

# 6. Configure Elastic Search
mv /etc/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml.orig
cp /vagrant/build_scripts/es_setup/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

# 7. Create data directory for Elastic Search
mkdir -p /data/es_logs
chown -R vagrant:vagrant /data
chmod 777 -R /data

# 8. Fix for max number of threads error when network.host: 0.0.0.0
bash -c "cat << 'EOF' >> /etc/security/limits.conf
elasticsearch - nproc 2048
elasticsearch - nofile 65536
EOF"

# 9. Start Elastic Search
sudo /etc/init.d/elasticsearch start

# 10. Setup sudo Access
cp /vagrant/build_scripts/es_setup/elasticsearch /etc/sudoers.d/elasticsearch
cp /vagrant/build_scripts/es_setup/nginx /etc/sudoers.d/nginx