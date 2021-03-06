#!/bin/bash

ELK_HOSTNAME=10.120.1.213
ELK_PORT=9200
FILEBEAT_JOURNALCTL_CONFIG="/etc/filebeat/filebeat_journald.yml"
FILEBEAT_JOURNALCTL_SERVICE=dcos-journalctl-filebeat.service

echo "** Installing Filebeat (aka. logstash-forwarder) ... "

#install filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-5.0.0-x86_64.rpm
sudo rpm -vi filebeat-5.0.0-x86_64.rpm

#configure filebeat
echo "** Configuring Filebeat (aka. logstash-forwarder) ..."
sudo mv /etc/filebeat/filebeat.yml /etc/filebeat/filebeat.yml.BAK
sudo tee /etc/filebeat/filebeat.yml <<-EOF 
filebeat.prospectors:
- input_type: log
  paths:
    - /var/lib/mesos/slave/slaves/*/frameworks/*/executors/*/runs/latest/stdout
    - /var/lib/mesos/slave/slaves/*/frameworks/*/executors/*/runs/latest/stderr
    - /var/log/mesos/*.log
    - /var/log/dcos/dcos.log
tail_files: true
output.elasticsearch:
  hosts: ["$ELK_HOSTNAME:$ELK_PORT"]
EOF

sudo mkdir -p /var/log/dcos

echo "** Creating service to parse DC/OS Agent logs into Filebeat ..."
sudo tee /etc/systemd/system/$FILEBEAT_JOURNALCTL_SERVICE<<-EOF 
[Unit]
Description=DCOS journalctl parser to filebeat
Wants=filebeat.service
After=filebeat.service
[Service]
Restart=always
RestartSec=5
ExecStart=/bin/sh -c '/usr/bin/journalctl --no-tail -f      \
  -u dcos-3dt.service                      \
  -u dcos-logrotate-agent.timer            \
  -u dcos-3dt.socket                       \
  -u dcos-mesos-slave.service              \
  -u dcos-adminrouter-agent.service        \
  -u dcos-minuteman.service                \
  -u dcos-adminrouter-reload.service       \
  -u dcos-navstar.service                  \
  -u dcos-adminrouter-reload.timer         \
  -u dcos-rexray.service                   \
  -u dcos-cfn-signal.service               \
  -u dcos-setup.service                    \
  -u dcos-download.service                 \
  -u dcos-signal.timer                     \
  -u dcos-epmd.service                     \
  -u dcos-spartan-watchdog.service         \
  -u dcos-gen-resolvconf.service           \
  -u dcos-spartan-watchdog.timer           \
  -u dcos-gen-resolvconf.timer             \
  -u dcos-spartan.service                  \
  -u dcos-link-env.service                 \
  -u dcos-vol-discovery-priv-agent.service \
  -u dcos-logrotate-agent.service          \
  > /var/log/dcos/dcos.log 2>&1'
ExecStartPre=/usr/bin/journalctl --vacuum-size=10M
[Install]
WantedBy=multi-user.target
EOF

echo "** Installed Filebeat (aka. logstash-forwarder) ... "

sudo chmod 0755 /etc/systemd/system/$FILEBEAT_JOURNALCTL_SERVICE
sudo systemctl daemon-reload
sudo systemctl start $FILEBEAT_JOURNALCTL_SERVICE
sudo chkconfig $FILEBEAT_JOURNALCTL_SERVICE on
sudo systemctl start filebeat
sudo chkconfig filebeat on
