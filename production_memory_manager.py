#!/usr/bin/env python3
"""
Production Memory Manager for Linux Host Environments
This script provides production-specific memory management for news generation.
"""

import psutil
import gc
import os
import time
import threading
import subprocess
import signal
from datetime import datetime
import ctypes
import sys

class ProductionMemoryManager:
    def __init__(self, max_memory_percent=65, cleanup_threshold=55, host_memory_threshold=80):
        self.max_memory_percent = max_memory_percent  # Container memory limit
        self.cleanup_threshold = cleanup_threshold   # When to cleanup
        self.host_memory_threshold = host_memory_threshold  # Host system memory limit
        self.monitoring = False
        self.monitor_thread = None
        self.is_containerized = self._check_if_containerized()
        
    def _check_if_containerized(self):
        """Check if running inside a Docker container."""
        try:
            # Check for container indicators
            if os.path.exists('/.dockerenv'):
                return True
            if os.path.exists('/sys/fs/cgroup/memory/memory.limit_in_bytes'):
                return True
            return False
        except:
            return False
    
    def get_host_memory_info(self):
        """Get host system memory information."""
        try:
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / 1024 / 1024 / 1024,
                'available_gb': memory.available / 1024 / 1024 / 1024,
                'used_gb': memory.used / 1024 / 1024 / 1024,
                'percent_used': memory.percent,
                'free_gb': memory.free / 1024 / 1024 / 1024
            }
        except Exception as e:
            print(f"Error getting host memory info: {e}")
            return None
    
    def get_container_memory_info(self):
        """Get container memory information."""
        if not self.is_containerized:
            return None
            
        try:
            # Get container memory limit
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                limit_bytes = int(f.read().strip())
            
            # Get current usage
            with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
                usage_bytes = int(f.read().strip())
            
            limit_mb = limit_bytes / 1024 / 1024
            usage_mb = usage_bytes / 1024 / 1024
            percent_used = (usage_bytes / limit_bytes) * 100
            
            return {
                'limit_mb': limit_mb,
                'usage_mb': usage_mb,
                'percent_used': percent_used,
                'available_mb': limit_mb - usage_mb
            }
        except Exception as e:
            print(f"Error getting container memory info: {e}")
            return None
    
    def aggressive_cleanup(self):
        """Perform aggressive memory cleanup."""
        try:
            print("🧹 Performing aggressive memory cleanup...")
            
            # Force garbage collection multiple times
            for i in range(5):  # More aggressive cleanup for production
                collected = gc.collect()
                print(f"   GC cycle {i+1}: collected {collected} objects")
                time.sleep(0.1)
            
            # Set very aggressive GC thresholds
            gc.set_threshold(5, 1, 1)
            
            # Try to trim memory on Linux systems
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                print("   ✅ Memory trimmed successfully")
            except:
                print("   ⚠️  Memory trim not available on this system")
            
            # Clear Python cache
            try:
                if hasattr(sys, '_clear_type_cache'):
                    sys._clear_type_cache()
                print("   ✅ Python type cache cleared")
            except:
                pass
            
            # Force memory compaction if available
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                print("   ✅ Memory compaction attempted")
            except:
                pass
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def check_memory_safe(self):
        """Check if memory usage is safe for news generation."""
        # Check host memory first
        host_info = self.get_host_memory_info()
        if host_info and host_info['percent_used'] > self.host_memory_threshold:
            return False, f"Host memory usage too high ({host_info['percent_used']:.1f}%)"
        
        # Check container memory if containerized
        if self.is_containerized:
            container_info = self.get_container_memory_info()
            if container_info and container_info['percent_used'] > self.max_memory_percent:
                return False, f"Container memory usage too high ({container_info['percent_used']:.1f}%)"
        
        return True, f"Memory usage OK (Host: {host_info['percent_used']:.1f}% if host_info else 'Unknown'})"
    
    def emergency_cleanup(self):
        """Emergency cleanup when memory is critically high."""
        print("🚨 EMERGENCY MEMORY CLEANUP INITIATED")
        
        # Multiple rounds of aggressive cleanup
        for round_num in range(3):
            print(f"   Emergency cleanup round {round_num + 1}/3")
            self.aggressive_cleanup()
            time.sleep(1)
        
        # Try to free system caches if possible
        try:
            # This requires root privileges
            subprocess.run(['sync'], check=False)
            subprocess.run(['echo', '3'], stdout=open('/proc/sys/vm/drop_caches', 'w'), check=False)
            print("   ✅ System caches cleared")
        except:
            print("   ⚠️  Could not clear system caches (requires root)")
        
        # Check memory after cleanup
        safe, message = self.check_memory_safe()
        print(f"   📊 After cleanup: {message}")
        return safe
    
    def start_monitoring(self):
        """Start background memory monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 Production memory monitoring started")
    
    def stop_monitoring(self):
        """Stop background memory monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🔍 Production memory monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                # Check host memory
                host_info = self.get_host_memory_info()
                if host_info:
                    if host_info['percent_used'] > self.host_memory_threshold:
                        print(f"🚨 CRITICAL: Host memory usage {host_info['percent_used']:.1f}% exceeds threshold!")
                        self.emergency_cleanup()
                
                # Check container memory if applicable
                if self.is_containerized:
                    container_info = self.get_container_memory_info()
                    if container_info and container_info['percent_used'] > self.cleanup_threshold:
                        print(f"⚠️  Container memory usage {container_info['percent_used']:.1f}% - performing cleanup")
                        self.aggressive_cleanup()
                
                time.sleep(5)  # Check every 5 seconds in production
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(5)
    
    def pre_generation_cleanup(self):
        """Cleanup before starting news generation."""
        print("🚀 Pre-generation memory cleanup...")
        
        # Check host memory first
        host_info = self.get_host_memory_info()
        if host_info and host_info['percent_used'] > self.host_memory_threshold:
            print(f"❌ Host memory usage too high ({host_info['percent_used']:.1f}%)")
            return False
        
        # Perform cleanup
        self.aggressive_cleanup()
        
        # Check if safe to proceed
        safe, message = self.check_memory_safe()
        if not safe:
            print(f"❌ {message}")
            return False
        
        print(f"✅ {message}")
        return True
    
    def post_generation_cleanup(self):
        """Cleanup after news generation."""
        print("🏁 Post-generation memory cleanup...")
        self.aggressive_cleanup()
        
        # Report final memory state
        host_info = self.get_host_memory_info()
        if host_info:
            print(f"📊 Final host memory usage: {host_info['percent_used']:.1f}%")
        
        if self.is_containerized:
            container_info = self.get_container_memory_info()
            if container_info:
                print(f"📊 Final container memory usage: {container_info['percent_used']:.1f}%")

# Global instance for easy access
production_memory_manager = ProductionMemoryManager()

def safe_production_news_generation(func):
    """Decorator to ensure safe memory usage during news generation in production."""
    def wrapper(*args, **kwargs):
        # Pre-generation cleanup
        if not production_memory_manager.pre_generation_cleanup():
            return {"error": "Memory usage too high - please try again later"}
        
        try:
            # Start monitoring
            production_memory_manager.start_monitoring()
            
            # Execute the function
            result = func(*args, **kwargs)
            
            return result
        finally:
            # Always cleanup after
            production_memory_manager.stop_monitoring()
            production_memory_manager.post_generation_cleanup()
    
    return wrapper

if __name__ == "__main__":
    # Test the production memory manager
    manager = ProductionMemoryManager()
    
    print("🧪 Testing Production Memory Manager...")
    print("=" * 50)
    
    # Test memory info
    host_info = manager.get_host_memory_info()
    if host_info:
        print(f"📊 Host Memory Usage:")
        print(f"   Total: {host_info['total_gb']:.1f} GB")
        print(f"   Used: {host_info['used_gb']:.1f} GB ({host_info['percent_used']:.1f}%)")
        print(f"   Available: {host_info['available_gb']:.1f} GB")
    
    container_info = manager.get_container_memory_info()
    if container_info:
        print(f"📊 Container Memory Usage:")
        print(f"   Limit: {container_info['limit_mb']:.0f} MB")
        print(f"   Used: {container_info['usage_mb']:.0f} MB ({container_info['percent_used']:.1f}%)")
        print(f"   Available: {container_info['available_mb']:.0f} MB")
    
    # Test cleanup
    print("\n🧹 Testing cleanup...")
    manager.aggressive_cleanup()
    
    # Test safety check
    safe, message = manager.check_memory_safe()
    print(f"\n✅ Safety Check: {message}")
    
    print(f"\n🎯 Production memory manager ready! (Containerized: {manager.is_containerized})")
