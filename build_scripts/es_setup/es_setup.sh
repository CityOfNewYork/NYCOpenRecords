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

    bash -c "printf '#\!/bin/bash\nsource /opt/rh/rh-nginx18/enable\n' > /etc/profile.d/nginx18.sh"

    mv /etc/opt/rh/rh-nginx18/nginx/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf.orig

    ln -s /vagrant/build_scripts/es_setup/nginx_conf/nginx.conf /etc/opt/rh/rh-nginx18/nginx/nginx.conf

    openssl req \
           -newkey rsa:4096 -nodes -keyout /vagrant/build_scripts/es_setup/elasticsearch_dev.key \
           -x509 -days 365 -out /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -subj "/C=US/ST=New York/L=New York/O=NYC Department of Records and Information Services/OU=IT/CN=womensactivism.nyc"
    openssl x509 -in /vagrant/build_scripts/es_setup/elasticsearch_dev.crt -out /vagrant/build_scripts/es_setup/elasticsearch_dev.pem -outform PEM

    sudo service rh-nginx18-nginx restart
fi

mkdir -p /data/es_logs
chown -R vagrant:vagrant /data
chmod 777 -R /data

# Fix for max number of threads error when network.host: 0.0.0.0
bash -c "cat << 'EOF' >> /etc/security/limits.conf
elasticsearch - nproc 2048
elasticsearch - nofile 65536
EOF"

# 5. Start Elasticsearch
sudo /etc/init.d/elasticsearch start

# 6. Default setup for searchguard plugin
sudo /etc/init.d/elasticsearch stop
sudo cp /vagrant/build_scripts/es_setup/search-guard-5.zip /tmp/
cd /tmp/
sudo unzip search-guard-5.zip
sudo mv search-guard-5 /usr/share/elasticsearch/plugins/
sudo chmod +x /usr/share/elasticsearch/plugins/search-guard-5/tools/install_configuration.sh
cd /usr/share/elasticsearch/plugins/search-guard-5/tools/
sudo ./install_configuration.sh -y
sudo /etc/init.d/elasticsearch start
# The following last line needs to run manually after the build scripts are finished. Will not work even with a vagrant reload
# sudo /usr/share/elasticsearch/plugins/search-guard-5/tools/sgadmin.sh -cd /usr/share/elasticsearch/plugins/search-guard-5/sgconfig -cn openrecords_development -ks /etc/elasticsearch/keystore.jks -ts /etc/elasticsearch/truststore.jks -nhnv -icl

# 7. Setup sudo Access
cp /vagrant/build_scripts/es_setup/elasticsearch /etc/sudoers.d/elasticsearch
cp /vagrant/build_scripts/es_setup/nginx /etc/sudoers.d/nginx