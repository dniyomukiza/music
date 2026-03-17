# Docker Image Backup Instructions

## Quick Start

### On Your Production Server (where Docker is running):

1. **Copy the backup script to your server:**
   ```bash
   scp backup-docker-images-complete.sh user@your-server:/path/to/music-1/
   ```

2. **SSH into your server and run:**
   ```bash
   cd /path/to/music-1
   chmod +x backup-docker-images-complete.sh
   ./backup-docker-images-complete.sh
   ```

3. **Verify backups were created:**
   ```bash
   ls -lh docker-image-backups/
   ```

## What Gets Backed Up

The complete backup saves **ALL images** used in your project:

### Third-party images (risky - could be removed):
- `deepcomp/icecast2` (~200-300MB)
- `phasecorex/liquidsoap:latest` (~300-400MB)

### Official base images (stable but good to have):
- `certbot/certbot` (~100-150MB)
- `python:3.10-slim` (~150-200MB)
- `nginx:alpine` (~50-100MB)

### Your built application images (CRITICAL):
- `myapp:latest` (varies, ~500MB-1GB+)
- `nginx-service` (if built, ~50-100MB)
- `fastapi-service` (if built, ~200-300MB)

**Total disk usage: ~1.5-2.5GB** (depending on your built images)

## Backup Location

Backups are saved to:
```
/path/to/music-1/docker-image-backups/
```

Files created (for each image):
- `image-name_YYYYMMDD_HHMMSS.tar` (timestamped backup)
- `image-name_latest.tar` (symlink to most recent backup)

Example:
- `icecast2_20241116_163000.tar` + `icecast2_latest.tar`
- `myapp_20241116_163000.tar` + `myapp_latest.tar`
- `python-3.10-slim_20241116_163000.tar` + `python-3.10-slim_latest.tar`
- etc.

## When to Run

- **Before major deployments** - Always backup before deploying
- **Monthly** - Regular backups to catch updates
- **After pulling new versions** - Backup immediately after updating

## Restore Images (if removed)

If images get removed from Docker Hub:

```bash
./restore-docker-images.sh
```

Or manually:
```bash
docker load -i docker-image-backups/icecast2_latest.tar
docker load -i docker-image-backups/liquidsoap_latest.tar
```

## Disk Space Management

### Keep Only Latest Backups
```bash
# Remove old timestamped backups, keep only latest symlinks
cd docker-image-backups
# Remove all timestamped backups, keep only *_latest.tar symlinks
find . -name "*_*.tar" ! -name "*_latest.tar" -type f -delete
```

**Note:** The `*_latest.tar` files are symlinks, so you need to keep at least one timestamped file for each image.

### Move Backups Off-Server (Recommended)
```bash
# Copy to external storage
scp docker-image-backups/*.tar user@backup-server:/backups/

# Or upload to cloud storage
aws s3 cp docker-image-backups/ s3://your-bucket/docker-backups/ --recursive
```

## Automated Backup (Optional)

Add to crontab for monthly backups:

```bash
# Edit crontab
crontab -e

# Add this line (runs 1st of every month at 2 AM)
0 2 1 * * cd /path/to/music-1 && ./backup-docker-images-complete.sh >> /var/log/docker-backup.log 2>&1
```

## Troubleshooting

### "Docker daemon is not running"
- Start Docker: `sudo systemctl start docker` (Linux) or start Docker Desktop (Mac/Windows)
- Or run on your production server where Docker is running

### "Image not found" during backup
- Script will use cached version if available
- If no cache, you'll need to pull the image first (if it still exists)

### Backup files are large
- This is normal: Docker images are compressed but still 200-400MB each
- Consider moving old backups to external storage

