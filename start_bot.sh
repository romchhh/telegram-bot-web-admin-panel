#!/bin/bash
source /root/WoldemarBot/myenv/bin/activate
nohup python3 /root/WoldemarBot/main.py > /dev/null 2>&1 &
