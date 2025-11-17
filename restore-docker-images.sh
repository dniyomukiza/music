#!/bin/bash
# Restore Docker Images Script
# Loads Docker images from tar files

set -e  # Exit on error

BACKUP_DIR="./docker-image-backups"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    echo "   Run backup-docker-images-complete.sh first"
    exit 1
fi

echo "🐳 Restoring Docker images from backups..."
echo ""

# Function to restore image
restore_image() {
    local backup_name=$1
    local backup_file="$BACKUP_DIR/${backup_name}_latest.tar"
    
    if [ ! -f "$backup_file" ]; then
        echo "⚠️  Backup not found: $backup_file"
        return 1
    fi
    
    echo "📦 Restoring: $backup_name"
    docker load -i "$backup_file" && {
        echo "✅ Restored: $backup_name"
    } || {
        echo "❌ Failed to restore $backup_name"
        return 1
    }
    echo ""
}

# Restore all images
echo "🔴 Restoring third-party images:"
restore_image "icecast2"
restore_image "liquidsoap"
echo ""

echo "🟡 Restoring official base images:"
restore_image "certbot"
restore_image "python-3.10-slim"
restore_image "nginx-alpine"
echo ""

echo "ℹ️  Skipping built images (myapp, nginx-service, fastapi-service)"
echo "   These can be rebuilt from Dockerfiles with: docker-compose build"
echo ""

echo "✨ Restoration complete!"
echo ""
echo "📋 Restored images:"
docker images | grep -E "(icecast2|liquidsoap|certbot|python|nginx)" || echo "No matching images found"

