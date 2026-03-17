#!/bin/bash

# Start Services Script for Music Application
# This script ensures Docker is running and starts all services with proper memory management

set -e

echo "🚀 Starting Music Application Services..."
echo "========================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    echo "   On macOS: Open Docker Desktop application"
    echo "   On Linux: sudo systemctl start docker"
    exit 1
fi

echo "✅ Docker is running"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

echo "✅ Found docker-compose.yml"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans || true

# Clean up any dangling containers or images
echo "🧹 Cleaning up Docker resources..."
docker system prune -f || true

# Build the application image
echo "🔨 Building application image..."
docker-compose build --no-cache app

# Start services with memory monitoring
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Check memory usage
echo "💾 Checking memory usage..."
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Test the application
echo "🧪 Testing application health..."
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Application is healthy and ready!"
else
    echo "⚠️  Application may still be starting up. Check logs with: docker-compose logs app"
fi

echo ""
echo "🎯 Services started successfully!"
echo "📱 Application URL: http://localhost:5000"
echo "📊 Monitor logs: docker-compose logs -f app"
echo "💾 Monitor memory: docker stats"
echo "🛑 Stop services: docker-compose down"
echo ""
echo "💡 For news generation, the system now has:"
echo "   - Increased memory limits (2GB)"
echo "   - Enhanced memory monitoring"
echo "   - Automatic cleanup and garbage collection"
echo "   - Lower memory thresholds for safety"

