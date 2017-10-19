#!/usr/bin/env bash
# 1. Install Java
yum -y install java-1.8.0-openjdk

wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.2.0.rpm -P /tmp

# 2. Install ElasticSearch
rpm -ivh /tmp/elasticsearch-5.2.0.rpm

# 3. Autostart ElasticSearch
sudo chkconfig --add elasticsearch
chkconfig elasticsearch on

# 4. Configure ElasticSearch
mv /etc/elasticsearch/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml.orig
ln -s /vagrant/build_scripts/es_setup/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

# Install nginx and create ssl certs if not running on a single server
if [ "$1" != single_server ]; then
    echo "complete complete complete COMPLETE"
    yum -y install rh-nginx18-nginx

    bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-nginx18/enable'"

    mv /etc/opt/rh/rh-nginx18/nginx/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf.orig

    ln -s /vagrant/build_scripts/es_setup/nginx_conf/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf

    openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/es_setup/elasticsearch_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=womensactivism.nyc"
    openssl x509 -in /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -out /vagrant/build_scripts/es_setup/elasticsearch_dev.pem -outform PEM

    sudo service rh-nginx18-nginx restartsudo
fi

mkdir -p /data/es_logs
chown -R vagrant:vagrant /data
chmod 777 -R /data

# Default setup for searchguard plugin
sudo cp /vagrant/build_scripts/es_setup/search-guard-5.zip /tmp/
cd /tmp/
sudo unzip search-guard-5.zip
sudo mv search-guard-5 /usr/share/elasticsearch/plugins/
#sudo unzip /usr/share/elasticsearch/plugins/search-guard-5.zip
#sudo rm -rf search-guard-5.zip
sudo cp /usr/share/elasticsearch/plugins/search-guard-5/tools/install_demo_configuration.sh /usr/share/elasticsearch/plugins/search-guard-5/tools/install_demo_configuration.sh.orig
sudo cp /vagrant/build_scripts/es_setup/install_demo_configuration.sh /usr/share/elasticsearch/plugins/search-guard-5/tools/
sudo chmod +x /usr/share/elasticsearch/plugins/search-guard-5/tools/install_demo_configuration.sh
cd /usr/share/elasticsearch/plugins/search-guard-5/tools/
sudo ./install_demo_configuration.sh -y
sudo /etc/init.d/elasticsearch start
sudo /usr/share/elasticsearch/plugins/search-guard-5/tools/sgadmin.sh -cd /usr/share/elasticsearch/plugins/search-guard-5/sgconfig -cn searchguard_demo -ks /etc/elasticsearch/kirk.jks -ts /etc/elasticsearch/truststore.jks -nhnv -icl

# 5. Start Elasticsearch
sudo /etc/init.d/elasticsearch start

# 6. Add the following lines to /etc/sudoers file
#openrecords_v2_0   ALL=(elasticsearch:elasticsearch) NOPASSWD:ALL
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch start
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch stop
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch status
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch restart
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch condrestart
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch try-restart
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch reload
#openrecords_v2_0   ALL=(ALL) NOPASSWD: /etc/init.d/elasticsearch force-reload
