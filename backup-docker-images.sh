#!/bin/bash
# Backup Docker Images Script
# Saves critical Docker images to tar files for disaster recovery

set -e  # Exit on error

BACKUP_DIR="./docker-image-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "🐳 Starting Docker image backup..."
echo "Backup directory: $BACKUP_DIR"
echo ""

# Function to save image
save_image() {
    local image_name=$1
    local backup_name=$2
    
    echo "📦 Pulling and saving: $image_name"
    
    # Pull latest version
    docker pull "$image_name" || {
        echo "⚠️  Warning: Failed to pull $image_name, using cached version if available"
    }
    
    # Save to tar file with timestamp
    local filename="${backup_name}_${TIMESTAMP}.tar"
    docker save "$image_name" -o "$BACKUP_DIR/$filename" && {
        echo "✅ Saved: $filename"
        
        # Also create a symlink to latest
        ln -sf "$filename" "$BACKUP_DIR/${backup_name}_latest.tar"
    } || {
        echo "❌ Failed to save $image_name"
        return 1
    }
    
    # Show file size
    local size=$(du -h "$BACKUP_DIR/$filename" | cut -f1)
    echo "   Size: $size"
    echo ""
}

# Save critical third-party images
save_image "deepcomp/icecast2" "icecast2"
save_image "phasecorex/liquidsoap:latest" "liquidsoap"
save_image "certbot/certbot" "certbot"

# Save official base images (good to have)
save_image "python:3.10-slim" "python-3.10-slim"
save_image "nginx:alpine" "nginx-alpine"

# Save your own built image if it exists
if docker images | grep -q "myapp.*latest"; then
    save_image "myapp:latest" "myapp"
else
    echo "ℹ️  Skipping myapp:latest (not found, will be built from Dockerfile)"
fi

echo "✨ Backup complete!"
echo ""
echo "📊 Backup summary:"
du -sh "$BACKUP_DIR"/*.tar 2>/dev/null | tail -1 || echo "No backups found"
echo ""
echo "💡 To restore an image later, run:"
echo "   docker load -i $BACKUP_DIR/<image-name>_latest.tar"
echo ""
echo "🗑️  To clean up old backups (keep last 5):"
echo "   ls -t $BACKUP_DIR/*.tar | tail -n +6 | xargs rm -f"

