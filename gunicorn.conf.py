# Gunicorn configuration file for memory optimization
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # Single worker for memory-constrained environments
worker_class = "sync"
worker_connections = 30  # Further reduced for better memory management
timeout = 1800  # 30 minutes timeout for long news generation tasks
keepalive = 2

# Memory management
max_requests = 0  # Disable automatic restarts to prevent interpreter shutdown during long tasks
max_requests_jitter = 0  # No jitter needed when max_requests is 0
preload_app = False  # Disable preload to reduce initial memory usage
worker_memory_limit = 2048  # Increased to 2GB for news generation

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
    'MALLOC_MMAP_THRESHOLD_=32768',  # Even smaller threshold
    'MALLOC_TRIM_THRESHOLD_=32768',  # More aggressive trimming
    'MALLOC_TOP_PAD_=32768',  # Reduced padding
    'MALLOC_MMAP_MAX_=16384',  # Fewer memory mappings
    'PYTHONHASHSEED=0',  # Consistent hashing
    'PYTHONDONTWRITEBYTECODE=1',  # Don't write .pyc files
    'PYTHONUNBUFFERED=1',  # Unbuffered output
    'PYTHONOPTIMIZE=1',  # Enable optimizations
    'PYTHONDONTWRITEBYTECODE=1',  # Don't write .pyc files
    'PYTHONIOENCODING=utf-8',  # Set encoding
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

def worker_exit(server, worker):
    """Called when a worker exits."""
    import gc
    gc.collect()  # Force garbage collection on worker exit

def on_exit(server):
    """Called when the master process exits."""
    import gc
    gc.collect()  # Final cleanup

def worker_abort(worker):
    """Called when a worker is aborted."""
    import gc
    gc.collect()  # Force garbage collection on worker abort

def pre_request(worker, req):
    """Called before processing each request."""
    import gc
    # Force garbage collection before each request
    gc.collect()

def post_request(worker, req, environ, resp):
    """Called after processing each request."""
    import gc
    # Force garbage collection after each request
    gc.collect()
