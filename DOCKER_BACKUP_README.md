# Docker Image Backup Guide

## Why Backup Docker Images?

Third-party Docker images can be removed by their maintainers, causing deployment failures. This backup system protects your production environment.

## Quick Start

### Backup Images (Run Monthly or Before Major Deployments)

```bash
./backup-docker-images.sh
```

This will:
- Pull latest versions of critical images
- Save them to `./docker-image-backups/` directory
- Create timestamped backups and symlinks to latest

### Restore Images (If Images Get Removed)

```bash
./restore-docker-images.sh
```

This will:
- Load all backed-up images from tar files
- Restore them to your Docker environment

## What Gets Backed Up

1. **Third-party images** (highest risk):
   - `deepcomp/icecast2` - Icecast streaming server
   - `phasecorex/liquidsoap:latest` - Audio streaming
   - `certbot/certbot` - SSL certificate management

2. **Base images** (good practice):
   - `python:3.10-slim` - Python runtime
   - `nginx:alpine` - Web server

3. **Your built images**:
   - `myapp:latest` - Your application (if built)

## Backup Schedule

**Recommended:**
- **Before major deployments** - Always backup before deploying
- **Monthly** - Regular backups to catch updates
- **After pulling new versions** - Backup immediately after updating

## Storage Considerations

- Each image backup is typically 100-500MB
- Total backup size: ~1-2GB for all images
- Old backups are kept (you can manually clean up)

## Manual Operations

### View Backup Files
```bash
ls -lh docker-image-backups/
```

### Load a Specific Image
```bash
docker load -i docker-image-backups/icecast2_latest.tar
```

### Clean Up Old Backups (Keep Last 5)
```bash
ls -t docker-image-backups/*.tar | tail -n +6 | xargs rm -f
```

### Check Image Sizes
```bash
docker images | grep -E "(icecast2|liquidsoap|certbot)"
```

## Integration with CI/CD

Add to your deployment pipeline:

```yaml
# Example GitHub Actions step
- name: Restore Docker Images
  run: |
    if [ -d "docker-image-backups" ]; then
      ./restore-docker-images.sh
    fi
```

## Troubleshooting

### "Image not found" error
- Run `./restore-docker-images.sh` to restore from backup
- Or rebuild from Dockerfile if backup unavailable

### Backup directory too large
- Delete old timestamped backups, keep only `*_latest.tar` files
- Or move backups to external storage (S3, etc.)

### Image pull fails during backup
- Script will use cached version if available
- Check your internet connection
- Verify image still exists on Docker Hub

## Best Practices

1. ✅ **Version control the scripts** (already in git)
2. ❌ **Don't commit backup tar files** (already in .gitignore)
3. ✅ **Store backups off-server** (copy to S3, external drive, etc.)
4. ✅ **Test restore process** periodically
5. ✅ **Document image sources** (this file!)

## Alternative: Use Image Digests

For even more stability, pin images by digest in `docker-compose.yml`:

```yaml
# Instead of: image: deepcomp/icecast2
# Use: image: deepcomp/icecast2@sha256:abc123...
```

Get digest:
```bash
docker inspect deepcomp/icecast2 | grep -i digest
```

