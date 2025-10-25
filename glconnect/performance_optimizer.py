"""
Memory Management Service for Ink Studio
Monitors and optimizes memory usage to prevent memory leaks
"""

import gc
import psutil
import os
import logging
from functools import wraps
from flask import current_app, g
import time

logger = logging.getLogger(__name__)

class MemoryManager:
    """Memory management utilities"""
    
    @staticmethod
    def get_memory_usage():
        """Get current memory usage statistics"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'available': psutil.virtual_memory().available,
            'total': psutil.virtual_memory().total
        }
    
    @staticmethod
    def log_memory_usage(context=""):
        """Log current memory usage"""
        memory = MemoryManager.get_memory_usage()
        logger.info(f"Memory usage {context}: {memory['percent']:.1f}% "
                   f"({memory['rss'] / 1024 / 1024:.1f} MB)")
    
    @staticmethod
    def cleanup_memory():
        """Force garbage collection and memory cleanup"""
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        return collected
    
    @staticmethod
    def check_memory_threshold(threshold_percent=80):
        """Check if memory usage exceeds threshold"""
        memory = MemoryManager.get_memory_usage()
        if memory['percent'] > threshold_percent:
            logger.warning(f"High memory usage: {memory['percent']:.1f}%")
            MemoryManager.cleanup_memory()
            return True
        return False

def memory_monitor(func):
    """Decorator to monitor memory usage of functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_memory = MemoryManager.get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_memory = MemoryManager.get_memory_usage()
            memory_diff = end_memory['rss'] - start_memory['rss']
            
            if memory_diff > 10 * 1024 * 1024:  # More than 10MB increase
                logger.warning(f"Function {func.__name__} increased memory by "
                             f"{memory_diff / 1024 / 1024:.1f} MB")
    
    return wrapper

class ConnectionPoolManager:
    """Database connection pool management"""
    
    @staticmethod
    def configure_pool(app):
        """Configure database connection pool for optimal performance"""
        from sqlalchemy import create_engine
        
        # Get current database URL
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if db_url:
            # Configure connection pool
            engine_options = {
                'pool_size': 10,  # Number of connections to maintain
                'max_overflow': 20,  # Additional connections beyond pool_size
                'pool_timeout': 30,  # Seconds to wait for connection
                'pool_recycle': 3600,  # Recycle connections after 1 hour
                'pool_pre_ping': True,  # Verify connections before use
                'echo': False,  # Set to True for SQL query logging
            }
            
            # Update engine with optimized settings
            if hasattr(app, 'extensions') and 'sqlalchemy' in app.extensions:
                engine = app.extensions['sqlalchemy'].db.engine
                engine.dispose()  # Close existing connections
                
                # Create new engine with optimized settings
                new_engine = create_engine(db_url, **engine_options)
                app.extensions['sqlalchemy'].db.engine = new_engine
                
                logger.info("Database connection pool optimized")

class StaticFileOptimizer:
    """Optimize static file serving"""
    
    @staticmethod
    def configure_static_optimization(app):
        """Configure static file optimization"""
        from flask import send_from_directory
        import gzip
        import os
        
        @app.route('/static/<path:filename>')
        def optimized_static(filename):
            """Serve static files with compression"""
            static_folder = app.static_folder
            
            # Check if file exists
            file_path = os.path.join(static_folder, filename)
            if not os.path.exists(file_path):
                return "File not found", 404
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Only compress files larger than 1KB
            if file_size > 1024:
                # Check if client accepts gzip
                from flask import request
                if 'gzip' in request.headers.get('Accept-Encoding', ''):
                    # Serve compressed version if available
                    gz_path = file_path + '.gz'
                    if os.path.exists(gz_path):
                        response = send_from_directory(static_folder, filename + '.gz')
                        response.headers['Content-Encoding'] = 'gzip'
                        response.headers['Content-Type'] = 'application/octet-stream'
                        return response
            
            return send_from_directory(static_folder, filename)

class ImageOptimizer:
    """Optimize image loading and serving"""
    
    @staticmethod
    def get_optimized_image_url(image_path, width=None, height=None, quality=80):
        """Generate optimized image URL with size parameters"""
        if not image_path:
            return None
        
        # For now, return original path
        # In production, you might want to integrate with image CDN
        return image_path
    
    @staticmethod
    def lazy_load_images():
        """Generate JavaScript for lazy loading images"""
        return """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        });
        </script>
        """

class PerformanceMiddleware:
    """Middleware for performance monitoring"""
    
    @staticmethod
    def init_app(app):
        """Initialize performance monitoring"""
        
        @app.before_request
        def before_request():
            g.start_time = time.time()
            MemoryManager.check_memory_threshold()
        
        @app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                if duration > 1.0:  # Log slow requests
                    logger.warning(f"Slow request: {duration:.3f}s")
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            return response

def optimize_app_performance(app):
    """Apply all performance optimizations to the app"""
    logger.info("Applying performance optimizations...")
    
    # Configure database connection pool
    ConnectionPoolManager.configure_pool(app)
    
    # Configure static file optimization
    StaticFileOptimizer.configure_static_optimization(app)
    
    # Initialize performance middleware
    PerformanceMiddleware.init_app(app)
    
    # Log initial memory usage
    MemoryManager.log_memory_usage("at startup")
    
    logger.info("Performance optimizations applied successfully")
