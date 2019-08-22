#/bin/bash
ps -eo pid,command | grep "java -jar /vagrant/executables/fakeSMTP-2.0.jar -s -b -p 2525 -a 127.0.0.1 -o /vagrant/tmp/emails/" | grep -v grep | awk '{print $1}' | xargs kill -9
java -jar /vagrant/executables/fakeSMTP-2.0.jar -s -b -p 2525 -a 127.0.0.1 -o /vagrant/tmp/emails/