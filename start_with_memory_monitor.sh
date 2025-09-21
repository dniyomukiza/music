#!/bin/bash

# Start the music application with memory monitoring
# This script starts both the application and the memory monitor

echo "🚀 Starting Music Application with Memory Monitoring"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the application with docker-compose
echo "📦 Starting application containers..."
docker-compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if application is running
if ! curl -s http://localhost:5000/routes2/news/debug/health > /dev/null; then
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo "✅ Application started successfully!"

# Start memory monitor in background
echo "🔍 Starting memory monitor..."
python3 memory_monitor_advanced.py &
MEMORY_MONITOR_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    echo "Stopping memory monitor (PID: $MEMORY_MONITOR_PID)..."
    kill $MEMORY_MONITOR_PID 2>/dev/null
    echo "Stopping application containers..."
    docker-compose down
    echo "👋 Shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🎵 Music Application is running!"
echo "📊 Memory Dashboard: http://localhost:5000/routes2/news/debug/memory-dashboard-page"
echo "🔧 Health Check: http://localhost:5000/routes2/news/debug/health"
echo "📰 News Generation: http://localhost:5000/routes2/news/"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running and show logs
docker-compose logs -f
