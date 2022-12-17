set -e

apt-get install -y cron
mkdir -p /root/back_ups
cp create_back_up.sh /root/
chmod 777 /root/create_back_up.sh
cp mega_cmd.service /etc/systemd/system
systemctl enable mega_cmd.service
systemctl daemon-reload
systemctl start mega_cmd.service
