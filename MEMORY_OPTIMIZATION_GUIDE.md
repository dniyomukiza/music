# Memory Optimization Guide

## Problem Analysis
Your application was experiencing memory issues with Gunicorn workers being killed due to memory constraints. The error message showed:
```
[2025-09-22 08:49:21 +0000] [7] [ERROR] Worker (pid:8) was sent SIGKILL! Perhaps out of memory?
```

## Solutions Implemented

### 1. Docker Compose Memory Limits
- **Added memory limits to FastAPI service**: 1GB limit, 512MB reservation
- **Added health checks** to all services for better monitoring
- **Added restart policies** to ensure services recover from failures

### 2. Gunicorn Configuration Optimizations
- **Reduced worker connections**: From 50 to 30 for better memory management
- **More frequent worker restarts**: From 25 to 15 requests per worker
- **Reduced worker memory limit**: From 400MB to 300MB per worker
- **Reduced timeout**: From 30 minutes to 20 minutes
- **Enhanced garbage collection**: Added more aggressive GC settings
- **Added worker exit cleanup**: Force garbage collection when workers exit

### 3. Health Monitoring
- **Added health endpoint**: `/health` endpoint provides memory usage information
- **Created monitoring script**: `memory_restart.sh` for automated monitoring and restart
- **Added service health checks**: Docker health checks for all services

### 4. Memory Management Scripts
- **Basic monitor**: `memory_monitor.py` for simple memory tracking
- **Advanced monitor**: `memory_monitor_advanced.py` with automatic restart capabilities
- **Restart script**: `memory_restart.sh` for automated service management

## How to Use

### 1. Restart Your Services
```bash
# Stop all services
docker-compose down

# Rebuild and start with new configuration
docker-compose up --build -d

# Check service status
docker-compose ps
```

### 2. Monitor Memory Usage
```bash
# Check current memory usage
./memory_restart.sh check

# Start continuous monitoring
./memory_restart.sh monitor

# Manual restart if needed
./memory_restart.sh restart
```

### 3. Check Health Endpoints
```bash
# Check main app health
curl http://localhost:5000/health

# Check FastAPI health (if implemented)
curl http://localhost:8002/health
```

### 4. Advanced Monitoring
```bash
# Run basic memory monitor for 5 minutes
python memory_monitor.py 300

# Run advanced monitor with auto-restart
python memory_monitor_advanced.py
```

## Configuration Details

### Memory Limits
- **Main App**: 4GB limit, 2GB reservation
- **FastAPI**: 1GB limit, 512MB reservation  
- **Icecast2**: 256MB limit, 128MB reservation
- **Liquidsoap**: 512MB limit, 256MB reservation

### Gunicorn Settings
- **Workers**: 1 (single worker for memory-constrained environments)
- **Max Requests**: 15 (restart workers every 15 requests)
- **Worker Memory Limit**: 300MB per worker
- **Timeout**: 20 minutes
- **Garbage Collection**: Aggressive settings for better memory cleanup

### Health Check Settings
- **Check Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts
- **Start Period**: 40-60 seconds

## Expected Results

1. **Reduced Memory Usage**: More frequent worker restarts prevent memory leaks
2. **Better Stability**: Health checks ensure services are running properly
3. **Automatic Recovery**: Monitoring script can restart services when memory is high
4. **Better Monitoring**: Health endpoints provide real-time memory information

## Troubleshooting

### If Services Still Crash
1. Check logs: `docker-compose logs app`
2. Monitor memory: `./memory_restart.sh monitor`
3. Check health: `curl http://localhost:5000/health`
4. Consider reducing memory limits further if needed

### If Health Checks Fail
1. Ensure `psutil` is installed: `pip install psutil`
2. Check if health endpoint is accessible: `curl http://localhost:5000/health`
3. Verify service is running: `docker-compose ps`

### Performance Considerations
- Single worker may reduce throughput but improves memory stability
- More frequent restarts may cause brief service interruptions
- Monitor logs to ensure the balance is appropriate for your use case

## Next Steps

1. **Deploy the changes** and monitor for 24-48 hours
2. **Adjust thresholds** based on your actual memory usage patterns
3. **Consider scaling** if single worker becomes a bottleneck
4. **Implement alerting** for production environments

## Files Modified
- `docker-compose.yml` - Added memory limits and health checks
- `gunicorn.conf.py` - Optimized memory management settings
- `glconnect/routes.py` - Added health endpoint
- `memory_restart.sh` - Created monitoring script
- `MEMORY_OPTIMIZATION_GUIDE.md` - This documentation
