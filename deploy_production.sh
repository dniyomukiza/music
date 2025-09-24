#!/bin/bash

# Production Deployment Script with Memory Management
# This script deploys the application to production with proper memory management

set -e

echo "🚀 Production Deployment with Memory Management"
echo "=============================================="

# Check if we're on a Linux system
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is designed for Linux production environments"
    echo "   Current OS: $OSTYPE"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    echo "   On Linux: sudo systemctl start docker"
    exit 1
fi

echo "✅ Docker is running"

# Check available memory
echo "💾 Checking system memory..."
TOTAL_MEM=$(free -h | awk '/^Mem:/ {print $2}')
AVAILABLE_MEM=$(free -h | awk '/^Mem:/ {print $7}')
MEM_USAGE=$(free | awk '/^Mem:/ {printf "%.1f", $3/$2 * 100}')

echo "   Total Memory: $TOTAL_MEM"
echo "   Available Memory: $AVAILABLE_MEM"
echo "   Memory Usage: ${MEM_USAGE}%"

# Check if memory is sufficient
if (( $(echo "$MEM_USAGE > 80" | bc -l) )); then
    echo "⚠️  WARNING: High memory usage detected (${MEM_USAGE}%)"
    echo "   Consider freeing up memory before deployment"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Docker memory usage
echo "🐳 Checking Docker memory usage..."
docker system df

# Clean up Docker resources
echo "🧹 Cleaning up Docker resources..."
docker system prune -f || true
docker volume prune -f || true

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans || true

# Build with no cache to ensure fresh build
echo "🔨 Building application with memory optimizations..."
docker-compose build --no-cache app

# Start services
echo "🚀 Starting services with memory management..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 30

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Check memory usage after deployment
echo "💾 Checking memory usage after deployment..."
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Run memory diagnostic
echo "🔍 Running memory diagnostic..."
python3 production_memory_diagnostic.py || echo "⚠️  Memory diagnostic failed"

# Test application health
echo "🧪 Testing application health..."
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Application is healthy and ready!"
else
    echo "⚠️  Application may still be starting up"
    echo "   Check logs with: docker-compose logs -f app"
fi

# Set up monitoring
echo "📊 Setting up memory monitoring..."
cat > /tmp/memory_monitor.sh << 'EOF'
#!/bin/bash
while true; do
    echo "$(date): Memory Usage"
    free -h
    echo "Docker Memory:"
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"
    echo "---"
    sleep 60
done
EOF

chmod +x /tmp/memory_monitor.sh

echo ""
echo "🎯 Production deployment completed!"
echo "📱 Application URL: http://localhost:5000"
echo "📊 Monitor memory: /tmp/memory_monitor.sh"
echo "📋 Check logs: docker-compose logs -f app"
echo "🛑 Stop services: docker-compose down"
echo ""
echo "💡 Memory optimizations applied:"
echo "   - Container memory limit: 2GB (increased from 1GB)"
echo "   - Memory reservation: 1GB (increased from 512MB)"
echo "   - Shared memory: 256MB (increased from 128MB)"
echo "   - Enhanced memory monitoring and cleanup"
echo "   - Production-specific memory management"
echo ""
echo "🔧 For news generation:"
echo "   - Start with 1-2 topics maximum"
echo "   - Monitor memory usage during generation"
echo "   - System will automatically cleanup memory"
echo "   - Emergency cleanup available if needed"
