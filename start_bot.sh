#!/bin/bash
source /root/telegram-bot-web-admin-panel/myenv/bin/activate
nohup python3 /root/telegram-bot-web-admin-panel/main.py > /dev/null 2>&1 &
