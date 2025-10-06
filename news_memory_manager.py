#!/usr/bin/env python3
"""
Enhanced memory management specifically for news generation.
This script provides better memory monitoring and cleanup for AI agent operations.
"""

import psutil
import gc
import os
import time
import threading
from datetime import datetime
import ctypes
import sys

class NewsMemoryManager:
    def __init__(self, max_memory_percent=85, cleanup_threshold=75):
        self.max_memory_percent = max_memory_percent
        self.cleanup_threshold = cleanup_threshold
        self.monitoring = False
        self.monitor_thread = None
        
    def get_memory_info(self):
        """Get detailed memory information."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'process_memory_mb': memory_info.rss / 1024 / 1024,
                'process_memory_percent': process.memory_percent(),
                'system_memory_total_gb': system_memory.total / 1024 / 1024 / 1024,
                'system_memory_available_gb': system_memory.available / 1024 / 1024 / 1024,
                'system_memory_used_percent': system_memory.percent,
                'system_memory_used_mb': system_memory.used / 1024 / 1024
            }
        except Exception as e:
            print(f"Error getting memory info: {e}")
            return None
    
    def aggressive_cleanup(self):
        """Perform aggressive memory cleanup."""
        try:
            print("🧹 Performing aggressive memory cleanup...")
            
            # Force garbage collection multiple times
            for i in range(3):
                collected = gc.collect()
                print(f"   GC cycle {i+1}: collected {collected} objects")
                time.sleep(0.1)
            
            # Set aggressive GC thresholds
            gc.set_threshold(10, 2, 2)
            
            # Try to trim memory on Linux systems
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                print("   ✅ Memory trimmed successfully")
            except:
                print("   ⚠️  Memory trim not available on this system")
            
            # Clear Python cache
            try:
                import sys
                if hasattr(sys, '_clear_type_cache'):
                    sys._clear_type_cache()
                print("   ✅ Python type cache cleared")
            except:
                pass
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def check_memory_safe(self):
        """Check if memory usage is safe for news generation."""
        mem_info = self.get_memory_info()
        if not mem_info:
            return False, "Could not get memory information"
        
        if mem_info['system_memory_used_percent'] > self.max_memory_percent:
            return False, f"Memory usage too high ({mem_info['system_memory_used_percent']:.1f}%)"
        
        return True, f"Memory usage OK ({mem_info['system_memory_used_percent']:.1f}%)"
    
    def start_monitoring(self):
        """Start background memory monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 News memory monitoring started")
    
    def stop_monitoring(self):
        """Stop background memory monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🔍 News memory monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                mem_info = self.get_memory_info()
                if mem_info:
                    if mem_info['system_memory_used_percent'] > self.cleanup_threshold:
                        print(f"⚠️  Memory usage high ({mem_info['system_memory_used_percent']:.1f}%) - performing cleanup")
                        self.aggressive_cleanup()
                
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(10)
    
    def pre_generation_cleanup(self):
        """Cleanup before starting news generation."""
        print("🚀 Pre-generation memory cleanup...")
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
        
        mem_info = self.get_memory_info()
        if mem_info:
            print(f"📊 Final memory usage: {mem_info['system_memory_used_percent']:.1f}%")

# Global instance for easy access
news_memory_manager = NewsMemoryManager()

def safe_news_generation(func):
    """Decorator to ensure safe memory usage during news generation."""
    def wrapper(*args, **kwargs):
        # Pre-generation cleanup
        if not news_memory_manager.pre_generation_cleanup():
            return {"error": "Memory usage too high - please try again later"}
        
        try:
            # Start monitoring
            news_memory_manager.start_monitoring()
            
            # Execute the function
            result = func(*args, **kwargs)
            
            return result
        finally:
            # Always cleanup after
            news_memory_manager.stop_monitoring()
            news_memory_manager.post_generation_cleanup()
    
    return wrapper

if __name__ == "__main__":
    # Test the memory manager
    manager = NewsMemoryManager()
    
    print("🧪 Testing News Memory Manager...")
    print("=" * 50)
    
    # Test memory info
    mem_info = manager.get_memory_info()
    if mem_info:
        print(f"📊 Current Memory Usage:")
        print(f"   Process: {mem_info['process_memory_mb']:.1f} MB")
        print(f"   System: {mem_info['system_memory_used_percent']:.1f}%")
        print(f"   Available: {mem_info['system_memory_available_gb']:.1f} GB")
    
    # Test cleanup
    print("\n🧹 Testing cleanup...")
    manager.aggressive_cleanup()
    
    # Test safety check
    safe, message = manager.check_memory_safe()
    print(f"\n✅ Safety Check: {message}")
    
    print("\n🎯 Memory manager ready for news generation!")

