#/bin/bash
ps -A -o pid,cmd | grep fakeSMTP | grep -v grep | head -n 1 | awk '{print $1}' | xargs kill -9
java -jar /vagrant/executables/fakeSMTP-2.0.jar -s -b -p 2525 -a 127.0.0.1 -o /vagrant/tmp/emails/