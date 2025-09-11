#!/usr/bin/env python3
"""
Memory monitoring script for the music application.
This script helps monitor memory usage and provides recommendations.
"""

import psutil
import os
import time
import sys

def get_memory_info():
    """Get current memory usage information."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Get system memory info
    system_memory = psutil.virtual_memory()
    
    return {
        'process_memory_mb': memory_info.rss / 1024 / 1024,
        'process_memory_percent': process.memory_percent(),
        'system_memory_total_gb': system_memory.total / 1024 / 1024 / 1024,
        'system_memory_available_gb': system_memory.available / 1024 / 1024 / 1024,
        'system_memory_used_percent': system_memory.percent
    }

def check_container_limits():
    """Check if running in a container and get memory limits."""
    try:
        # Check for cgroup memory limit
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            limit_bytes = int(f.read().strip())
            return limit_bytes / 1024 / 1024 / 1024  # Convert to GB
    except:
        return None

def monitor_memory(duration_seconds=60, interval=5):
    """Monitor memory usage for a specified duration."""
    print("🔍 Memory Monitor Starting...")
    print("=" * 50)
    
    container_limit = check_container_limits()
    if container_limit:
        print(f"📦 Container Memory Limit: {container_limit:.2f} GB")
    else:
        print("🖥️  Running on host system")
    
    print(f"⏱️  Monitoring for {duration_seconds} seconds (checking every {interval}s)")
    print("=" * 50)
    
    start_time = time.time()
    max_memory = 0
    
    while time.time() - start_time < duration_seconds:
        mem_info = get_memory_info()
        max_memory = max(max_memory, mem_info['process_memory_mb'])
        
        print(f"📊 Process Memory: {mem_info['process_memory_mb']:.1f} MB "
              f"({mem_info['process_memory_percent']:.1f}%) | "
              f"System: {mem_info['system_memory_used_percent']:.1f}% used")
        
        # Warning if memory usage is high
        if mem_info['process_memory_mb'] > 200:
            print("⚠️  WARNING: High memory usage detected!")
        
        if container_limit and mem_info['process_memory_mb'] > container_limit * 1024 * 0.8:
            print("🚨 CRITICAL: Approaching container memory limit!")
        
        time.sleep(interval)
    
    print("=" * 50)
    print(f"📈 Peak Memory Usage: {max_memory:.1f} MB")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if max_memory > 200:
        print("   - Consider reducing worker count in gunicorn.conf.py")
        print("   - Enable more aggressive garbage collection")
        print("   - Check for memory leaks in image generation")
    
    if container_limit and max_memory > container_limit * 1024 * 0.7:
        print("   - Increase container memory limit")
        print("   - Optimize memory-intensive operations")
        print("   - Consider using external services for heavy processing")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    else:
        duration = 60
    
    monitor_memory(duration)
