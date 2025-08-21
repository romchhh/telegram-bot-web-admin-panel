#!/bin/bash
source /root/WoldemarBot/myenv/bin/activate
nohup python3 /root/WoldemarBot/cron_daemon.py > /dev/null 2>&1 &
echo "🔄 Starting cron daemon..."
