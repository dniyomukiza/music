# Gunicorn configuration file for memory optimization
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # Single worker for memory-constrained environments
worker_class = "sync"
worker_connections = 50  # Reduced for news generation
timeout = 1800  # Increased timeout for news generation (30 minutes)
keepalive = 2

# Memory management
max_requests = 25  # Restart workers more frequently to prevent memory leaks
max_requests_jitter = 5  # Add randomness to prevent all workers restarting at once
preload_app = False  # Disable preload to reduce initial memory usage
worker_memory_limit = 400  # Increased memory limit for news generation

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'music_app'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Memory optimization
worker_tmp_dir = "/dev/shm"  # Use shared memory for temporary files

# Environment variables for memory optimization
raw_env = [
    'MALLOC_ARENA_MAX=1',  # Reduce memory fragmentation
    'MALLOC_MMAP_THRESHOLD_=65536',  # Smaller threshold
    'MALLOC_TRIM_THRESHOLD_=65536',  # More aggressive trimming
    'MALLOC_TOP_PAD_=65536',  # Reduced padding
    'MALLOC_MMAP_MAX_=32768',  # Fewer memory mappings
    'PYTHONHASHSEED=0',  # Consistent hashing
    'PYTHONDONTWRITEBYTECODE=1',  # Don't write .pyc files
    'PYTHONUNBUFFERED=1',  # Unbuffered output
]

# Additional memory optimizations
def on_starting(server):
    """Called just before the master process is initialized."""
    import gc
    gc.set_threshold(100, 10, 10)  # More aggressive garbage collection

def worker_int(worker):
    """Called just after a worker has been forked."""
    import gc
    gc.set_threshold(50, 5, 5)  # Even more aggressive GC in workers

def max_requests_jitter_handler(worker):
    """Called when max_requests is reached."""
    import gc
    gc.collect()  # Force garbage collection before restart
