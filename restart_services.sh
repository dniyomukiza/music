#!/bin/bash

echo "🔄 Restarting services to clear memory..."

# Stop services
echo "Stopping services..."
docker-compose down

# Wait a moment
sleep 5

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check status
echo "Checking service status..."
docker-compose ps

# Check memory status
echo "Checking memory status..."
curl -s http://localhost:5000/routes2/news/memory-status | python3 -m json.tool

echo "✅ Services restarted successfully!"
