#!/usr/bin/env bash

# Copyright (c) 2021-2025 tteck
# Author: tteck (tteckster)
# License: MIT
# https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE

source /dev/stdin <<< "$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

# 🚀 Set Redis Password
REDIS_PASSWORD="YourStrongRedisPasswordHere"  # CHANGE THIS

msg_info "Installing Dependencies"
$STD apt-get install -y curl sudo mc apt-transport-https gpg lsb-release python3 python3-pip git unzip
msg_ok "Installed Base Dependencies"

# 🚀 Install Node.js & PM2
msg_info "Installing Node.js & PM2"
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -   # Install Node.js 18
$STD apt-get install -y nodejs
npm install -g pm2
msg_ok "Installed Node.js & PM2"

# 🚀 Install Redis
msg_info "Installing Redis"
wget -qO- https://packages.redis.io/gpg | gpg --dearmor >/usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" >/etc/apt/sources.list.d/redis.list
$STD apt-get update
$STD apt-get install -y redis
sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf

# 🚀 Apply Redis Password
echo "requirepass $REDIS_PASSWORD" >> /etc/redis/redis.conf
echo "masterauth $REDIS_PASSWORD" >> /etc/redis/redis.conf

# 🚀 Allocate More RAM for Redis
echo "maxmemory 6gb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf

# 🚀 Optimize for High Connections
echo "tcp-backlog 1024" >> /etc/redis/redis.conf
echo "timeout 0" >> /etc/redis/redis.conf
echo "tcp-keepalive 300" >> /etc/redis/redis.conf

# 🚀 Improve Replication Performance
echo "repl-backlog-size 256mb" >> /etc/redis/redis.conf
echo "repl-timeout 60" >> /etc/redis/redis.conf

# 🚀 Enable Cluster Mode
echo "cluster-enabled yes" >> /etc/redis/redis.conf
echo "cluster-config-file nodes.conf" >> /etc/redis/redis.conf
echo "cluster-node-timeout 5000" >> /etc/redis/redis.conf

# 🚀 Enable Redis Persistence (AOF + RDB)
echo "save 900 1" >> /etc/redis/redis.conf   # Save every 15 minutes if at least 1 change
echo "save 300 10" >> /etc/redis/redis.conf  # Save every 5 minutes if at least 10 changes
echo "save 60 1000" >> /etc/redis/redis.conf # Save every 60 seconds if 1000 changes
echo "appendonly yes" >> /etc/redis/redis.conf  # Enable AOF (Append Only File)
echo "appendfsync everysec" >> /etc/redis/redis.conf  # Sync AOF every second

systemctl enable -q --now redis-server.service
msg_ok "Installed Redis with Optimized Settings"

# 🚀 Increase CPU, RAM, and HDD in Proxmox LXC Config
if [ -f "/etc/pve/lxc/${CTID}.conf" ]; then
    echo "lxc.cgroup2.cpu.max = \"400000 1000000\"" >> /etc/pve/lxc/${CTID}.conf
    echo "lxc.cgroup2.memory.max = 6G" >> /etc/pve/lxc/${CTID}.conf
    echo "lxc.cgroup2.memory.swap.max = 0" >> /etc/pve/lxc/${CTID}.conf
    echo "mp0: local-lvm:vm-100-disk-0,size=20G" >> /etc/pve/lxc/${CTID}.conf  # Set HDD to 20GB
fi

# 🚀 Set Up PM2 for Redis Monitoring
msg_info "Setting up PM2 to Monitor Redis"
pm2 start "redis-server /etc/redis/redis.conf" --name redis-shard
pm2 save
pm2 startup systemd | bash
msg_ok "PM2 Redis Monitoring Enabled"

# 🚀 Set Up Automatic Redis Backups to Your Bucket
msg_info "Setting up Redis Backup"
mkdir -p /root/backups
echo '#!/bin/bash
timestamp=$(date +"%Y%m%d_%H%M%S")
redis-cli -a '$REDIS_PASSWORD' save
cp /var/lib/redis/dump.rdb /root/backups/redis-backup-$timestamp.rdb
curl -X PUT --upload-file /root/backups/redis-backup-$timestamp.rdb YourS3BucketURLHere
' > /root/redis-backup.sh
chmod +x /root/redis-backup.sh
(crontab -l 2>/dev/null; echo "0 * * * * /root/redis-backup.sh") | crontab -
msg_ok "Redis Automatic Backup Scheduled"

motd_ssh
customize

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"

msg_info "Restarting Redis to Apply Changes"
systemctl restart redis
msg_ok "Redis Restarted with Optimized Configuration"
