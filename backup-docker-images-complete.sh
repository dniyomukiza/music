#!/bin/bash
# Docker Image Backup - External Images Only
# Backs up external images that could be removed:
# - Third-party images (risky - could disappear)
# - Official base images (stable but good to have backups)
# 
# Note: Built images (myapp, nginx-service, fastapi-service) are NOT backed up
#       because they can be rebuilt from Dockerfiles

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

echo "🐳 Docker image backup - External images only..."
echo "Backup location: $(pwd)/$BACKUP_DIR"
echo ""
echo "This will backup:"
echo "  • Third-party images (icecast2, liquidsoap)"
echo "  • Official base images (python, nginx, certbot)"
echo ""
echo "Note: Built images (myapp, nginx-service, fastapi-service) are skipped"
echo "      because they can be rebuilt from Dockerfiles"
echo ""

# Backup external images only (not built images)
# This includes base images and third-party images that could be removed

save_image() {
    local image_name=$1
    local backup_name=$2
    
    echo "📦 Saving: $image_name"
    
    # Try to pull latest (will use cache if already exists)
    docker pull "$image_name" 2>/dev/null || echo "   Using cached version"
    
    # Check if image exists locally (handle both with and without registry prefix)
    local image_exists=false
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image_name}$"; then
        image_exists=true
    elif docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "docker.io/${image_name}$"; then
        image_exists=true
        image_name="docker.io/${image_name}"
    elif docker images "$image_name" --format "{{.Repository}}:{{.Tag}}" | grep -q .; then
        image_exists=true
    fi
    
    if [ "$image_exists" = false ]; then
        echo "⚠️  Image not found locally: $image_name"
        echo "   Trying to use image as-is..."
        # Try to save anyway - docker save might work with the name
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

# Note: myapp is NOT backed up - it's built from Dockerfile and can be rebuilt
# Only backing up external images that could be removed
echo "ℹ️  Skipping myapp (built from Dockerfile - can be rebuilt)"
echo "ℹ️  Skipping nginx-service and fastapi-service (built from Dockerfiles)"

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

