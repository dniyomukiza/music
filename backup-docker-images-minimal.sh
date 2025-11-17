#!/bin/bash
# Complete Docker Image Backup
# Backs up ALL images used in the project:
# - Third-party images (risky)
# - Official base images (stable but good to have)
# - Your built application images (critical)

set -e

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running!"
    echo "   Please start Docker or run this script on your server where Docker is running."
    exit 1
fi

BACKUP_DIR="./docker-image-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "🐳 Complete Docker image backup..."
echo "Backup location: $(pwd)/$BACKUP_DIR"
echo ""
echo "This will backup:"
echo "  • Third-party images (icecast2, liquidsoap)"
echo "  • Official base images (python, nginx, certbot)"
echo "  • Your built images (myapp, nginx-service, fastapi-service)"
echo ""

# Backup ALL images used in the project
# This includes base images, third-party images, and your built images

save_image() {
    local image_name=$1
    local backup_name=$2
    
    echo "📦 Saving: $image_name"
    
    # Try to pull latest (will use cache if already exists)
    docker pull "$image_name" 2>/dev/null || echo "   Using cached version"
    
    # Check if image exists locally
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image_name}$"; then
        echo "⚠️  Image not found locally: $image_name"
        return 1
    fi
    
    local filename="${backup_name}_${TIMESTAMP}.tar"
    docker save "$image_name" -o "$BACKUP_DIR/$filename" && {
        echo "✅ Saved: $filename"
        ln -sf "$filename" "$BACKUP_DIR/${backup_name}_latest.tar"
        du -h "$BACKUP_DIR/$filename" | cut -f1 | xargs echo "   Size:"
    } || {
        echo "❌ Failed to save $image_name"
        return 1
    }
    echo ""
}

# Third-party images (risky - could be removed)
echo "🔴 Third-party images (high priority):"
save_image "deepcomp/icecast2" "icecast2"
save_image "phasecorex/liquidsoap:latest" "liquidsoap"
echo ""

# Official images (stable but good to have backups)
echo "🟡 Official base images:"
save_image "certbot/certbot" "certbot"
save_image "python:3.10-slim" "python-3.10-slim"
save_image "nginx:alpine" "nginx-alpine"
echo ""

# Your built images (CRITICAL - these are your app!)
echo "🟢 Your built images (critical):"
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^myapp:latest$"; then
    save_image "myapp:latest" "myapp"
else
    echo "⚠️  myapp:latest not found (build it first with: docker-compose build app)"
fi

# Check for nginx and fastapi built images
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "nginx_service"; then
    nginx_image=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "nginx_service" | head -1)
    save_image "$nginx_image" "nginx-service"
fi

if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "fastapi"; then
    fastapi_image=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "fastapi" | head -1)
    save_image "$fastapi_image" "fastapi-service"
fi

echo "✨ Complete backup finished!"
echo ""
echo "📊 Backup summary:"
if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR/*.tar 2>/dev/null)" ]; then
    echo "Total size:"
    du -sh "$BACKUP_DIR" 2>/dev/null
    echo ""
    echo "Backed up images:"
    ls -lh "$BACKUP_DIR"/*_latest.tar 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
else
    echo "No backups created"
fi
echo ""
echo "💡 To restore images later:"
echo "   ./restore-docker-images.sh"
echo ""
echo "💡 Tip: Store these backups off-server (S3, external drive) to save disk space"

