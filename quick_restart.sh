#!/bin/bash

# Quick restart script for emergency memory situations
# This script provides fast service restarts when memory issues occur

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "quick_restart.log"
}

quick_restart() {
    local service_name=$1
    log "${YELLOW}Quick restarting $service_name...${NC}"
    
    # Force stop the container
    docker stop "$service_name" 2>/dev/null || true
    
    # Wait a moment
    sleep 2
    
    # Start the container
    docker start "$service_name" 2>/dev/null || true
    
    # Wait for service to be ready
    sleep 5
    
    log "${GREEN}$service_name quick restarted${NC}"
}

emergency_restart_all() {
    log "${RED}EMERGENCY RESTART ALL SERVICES${NC}"
    
    # Stop all services
    docker-compose down --timeout=10
    
    # Wait
    sleep 5
    
    # Start all services
    docker-compose up -d
    
    log "${GREEN}All services emergency restarted${NC}"
}

check_memory() {
    local memory_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    echo "Current memory usage: ${memory_percent}%"
    
    if [ "$memory_percent" -gt 80 ]; then
        echo "${RED}CRITICAL: Memory usage is ${memory_percent}%${NC}"
        return 1
    elif [ "$memory_percent" -gt 60 ]; then
        echo "${YELLOW}WARNING: Memory usage is ${memory_percent}%${NC}"
        return 2
    else
        echo "${GREEN}Memory usage is ${memory_percent}% - OK${NC}"
        return 0
    fi
}

# Main execution
case "${1:-help}" in
    "app")
        quick_restart "myapp"
        ;;
    "fastapi")
        quick_restart "fastapi"
        ;;
    "liquidsoap")
        quick_restart "liquidsoap_service"
        ;;
    "icecast")
        quick_restart "icecast_server"
        ;;
    "all")
        emergency_restart_all
        ;;
    "check")
        check_memory
        ;;
    "monitor")
        while true; do
            check_memory
            if [ $? -eq 1 ]; then
                log "${RED}Critical memory usage detected, restarting app...${NC}"
                quick_restart "myapp"
            fi
            sleep 10
        done
        ;;
    *)
        echo "Usage: $0 {app|fastapi|liquidsoap|icecast|all|check|monitor}"
        echo "  app       - Quick restart main app"
        echo "  fastapi   - Quick restart FastAPI service"
        echo "  liquidsoap- Quick restart Liquidsoap service"
        echo "  icecast   - Quick restart Icecast service"
        echo "  all       - Emergency restart all services"
        echo "  check     - Check current memory usage"
        echo "  monitor   - Monitor memory and auto-restart"
        exit 1
        ;;
esac
