#!/bin/bash
echo "🌐 Starting web server on http://localhost:5001"
echo "🔐 Login: Woldemar | Password: SamaraBoy777.V"
    
source /root/telegram-bot-web-admin-panel//myenv/bin/activate
nohup python3 /root/telegram-bot-web-admin-panel/web_admin.py > /dev/null 2>&1 &
