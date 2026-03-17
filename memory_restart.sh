#!/bin/bash

# Memory monitoring and restart script for music application
# This script monitors memory usage and restarts services when needed

set -e

# Configuration
MEMORY_THRESHOLD=85  # Percentage threshold for warning
RESTART_THRESHOLD=95  # Percentage threshold for restart
CHECK_INTERVAL=30    # Check every 30 seconds
LOG_FILE="memory_restart.log"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_memory_usage() {
    # Get system memory usage percentage
    memory_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    echo "$memory_percent"
}

check_service_health() {
    local service_name=$1
    local health_url=$2
    
    if curl -f -s "$health_url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

restart_service() {
    local service_name=$1
    log "${YELLOW}Restarting $service_name service...${NC}"
    
    if docker-compose restart "$service_name" > /dev/null 2>&1; then
        log "${GREEN}Successfully restarted $service_name${NC}"
        return 0
    else
        log "${RED}Failed to restart $service_name${NC}"
        return 1
    fi
}

monitor_memory() {
    log "${GREEN}Starting memory monitoring...${NC}"
    log "Memory threshold: ${MEMORY_THRESHOLD}%"
    log "Restart threshold: ${RESTART_THRESHOLD}%"
    log "Check interval: ${CHECK_INTERVAL}s"
    
    while true; do
        memory_usage=$(get_memory_usage)
        current_time=$(date '+%H:%M:%S')
        
        # Check memory usage
        if [ "$memory_usage" -ge "$RESTART_THRESHOLD" ]; then
            log "${RED}CRITICAL: Memory usage is ${memory_usage}% - restarting services${NC}"
            
            # Restart services in order of priority
            restart_service "app"
            sleep 10
            restart_service "fastapi"
            sleep 10
            restart_service "liquidsoap"
            
            # Wait for services to stabilize
            log "Waiting for services to stabilize..."
            sleep 60
            
        elif [ "$memory_usage" -ge "$MEMORY_THRESHOLD" ]; then
            log "${YELLOW}WARNING: Memory usage is ${memory_usage}%${NC}"
            
            # Check service health
            if ! check_service_health "app" "http://localhost:5000/health"; then
                log "${YELLOW}App service unhealthy, restarting...${NC}"
                restart_service "app"
            fi
            
        else
            log "${GREEN}Memory usage: ${memory_usage}% - OK${NC}"
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Main execution
case "${1:-monitor}" in
    "monitor")
        monitor_memory
        ;;
    "check")
        memory_usage=$(get_memory_usage)
        echo "Current memory usage: ${memory_usage}%"
        ;;
    "restart")
        restart_service "app"
        restart_service "fastapi"
        restart_service "liquidsoap"
        ;;
    *)
        echo "Usage: $0 {monitor|check|restart}"
        echo "  monitor  - Start continuous monitoring (default)"
        echo "  check    - Check current memory usage"
        echo "  restart  - Restart all services"
        exit 1
        ;;
esac
