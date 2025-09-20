#!/bin/bash

# Bot monitoring script
# This script checks if the bot is running and restarts it if needed

# Configuration
BOT_NAME="WoldemarBot2"
BOT_DIR="/root/telegram-bot-web-admin-panel"  # Your actual bot directory
BOT_SCRIPT="main.py"  # or whatever your main bot file is called
LOG_FILE="/var/log/bot_monitor.log"
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN=60  # seconds between restart attempts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if bot is running
is_bot_running() {
    pgrep -f "$BOT_SCRIPT" > /dev/null 2>&1
    return $?
}

# Function to start the bot
start_bot() {
    log_message "${YELLOW}Starting $BOT_NAME...${NC}"
    cd "$BOT_DIR" || {
        log_message "${RED}ERROR: Cannot change to directory $BOT_DIR${NC}"
        return 1
    }
    
    # Activate virtual environment if it exists
    if [ -f "myenv/bin/activate" ]; then
        source myenv/bin/activate
        log_message "Virtual environment activated"
    fi
    
    # Start the bot in background
    nohup python3 "$BOT_SCRIPT" > "bot_output.log" 2>&1 &
    BOT_PID=$!
    
    # Wait a moment and check if it started successfully
    sleep 5
    if is_bot_running; then
        log_message "${GREEN}$BOT_NAME started successfully with PID $BOT_PID${NC}"
        return 0
    else
        log_message "${RED}ERROR: Failed to start $BOT_NAME${NC}"
        return 1
    fi
}

# Function to stop the bot
stop_bot() {
    log_message "${YELLOW}Stopping $BOT_NAME...${NC}"
    pkill -f "$BOT_SCRIPT"
    sleep 3
    
    # Force kill if still running
    if is_bot_running; then
        log_message "${YELLOW}Force killing $BOT_NAME...${NC}"
        pkill -9 -f "$BOT_SCRIPT"
        sleep 2
    fi
}

# Function to restart the bot
restart_bot() {
    log_message "${YELLOW}Restarting $BOT_NAME...${NC}"
    stop_bot
    sleep 2
    start_bot
}

# Main monitoring logic
main() {
    log_message "=== Bot Monitor Started ==="
    
    # Check if bot directory exists
    if [ ! -d "$BOT_DIR" ]; then
        log_message "${RED}ERROR: Bot directory $BOT_DIR does not exist${NC}"
        exit 1
    fi
    
    # Check if bot script exists
    if [ ! -f "$BOT_DIR/$BOT_SCRIPT" ]; then
        log_message "${RED}ERROR: Bot script $BOT_SCRIPT not found in $BOT_DIR${NC}"
        exit 1
    fi
    
    # Initialize restart counter
    restart_count=0
    last_restart_time=0
    
    while true; do
        if is_bot_running; then
            log_message "${GREEN}$BOT_NAME is running normally${NC}"
            restart_count=0  # Reset counter on successful check
        else
            current_time=$(date +%s)
            
            # Check if we're in cooldown period
            if [ $((current_time - last_restart_time)) -lt $RESTART_COOLDOWN ]; then
                log_message "${YELLOW}$BOT_NAME is down, but still in cooldown period${NC}"
            else
                # Check restart limit
                if [ $restart_count -ge $MAX_RESTART_ATTEMPTS ]; then
                    log_message "${RED}ERROR: Maximum restart attempts ($MAX_RESTART_ATTEMPTS) reached. Manual intervention required.${NC}"
                    exit 1
                fi
                
                log_message "${RED}$BOT_NAME is not running! Attempting restart...${NC}"
                restart_bot
                
                if [ $? -eq 0 ]; then
                    restart_count=$((restart_count + 1))
                    last_restart_time=$current_time
                    log_message "${GREEN}Restart attempt $restart_count completed${NC}"
                else
                    log_message "${RED}Restart attempt $restart_count failed${NC}"
                    restart_count=$((restart_count + 1))
                    last_restart_time=$current_time
                fi
            fi
        fi
        
        # Wait before next check
        sleep 30
    done
}

# Handle script termination
cleanup() {
    log_message "Bot monitor stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run main function
main
