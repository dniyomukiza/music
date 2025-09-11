# Gunicorn configuration file for memory optimization
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 2  # Reduced from default to save memory
worker_class = "sync"
worker_connections = 1000
timeout = 60  # Increased timeout to prevent worker kills
keepalive = 2

# Memory management
max_requests = 500  # Restart workers more frequently to prevent memory leaks
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
preload_app = True  # Load application before forking workers
worker_memory_limit = 200  # Kill workers that exceed 200MB memory usage

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
    'MALLOC_ARENA_MAX=2',
    'MALLOC_MMAP_THRESHOLD_=131072',
    'MALLOC_TRIM_THRESHOLD_=131072',
    'MALLOC_TOP_PAD_=131072',
    'MALLOC_MMAP_MAX_=65536',
]
