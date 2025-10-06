#!/usr/bin/env python3
"""
Test script to verify memory monitoring in production container.
Run this inside the container to check memory detection.
"""

import os
import psutil

def test_memory_monitoring():
    """Test the memory monitoring function."""
    print("🧪 Testing Memory Monitoring in Production Container")
    print("=" * 60)
    
    # Test system memory info
    memory_info = psutil.virtual_memory()
    print(f"📊 System Memory Info:")
    print(f"   Total: {memory_info.total / 1024 / 1024:.1f} MB")
    print(f"   Used: {memory_info.used / 1024 / 1024:.1f} MB")
    print(f"   Available: {memory_info.available / 1024 / 1024:.1f} MB")
    print(f"   Percent: {memory_info.percent:.1f}%")
    
    # Test cgroup detection
    print(f"\n🔍 Cgroup Detection:")
    cgroup_paths = [
        '/sys/fs/cgroup/memory.max',
        '/sys/fs/cgroup/memory/memory.max',
        '/sys/fs/cgroup/system.slice/docker-myapp.scope/memory.max',
        '/sys/fs/cgroup/memory/memory.limit_in_bytes'
    ]
    
    for path in cgroup_paths:
        try:
            with open(path, 'r') as f:
                content = f.read().strip()
                print(f"   ✅ {path}: {content}")
        except Exception as e:
            print(f"   ❌ {path}: {e}")
    
    # Test the actual memory monitoring function
    print(f"\n🎯 Memory Monitoring Function Test:")
    try:
        from glconnect.news_agent import get_memory_usage
        memory_percent = get_memory_usage()
        print(f"   Memory Usage: {memory_percent:.1f}%")
        
        # Check thresholds
        print(f"\n📏 Threshold Check:")
        print(f"   Warning (80%): {'⚠️  WARNING' if memory_percent > 80 else '✅ OK'}")
        print(f"   Critical (90%): {'🚨 CRITICAL' if memory_percent > 90 else '✅ OK'}")
        print(f"   Blocking (95%): {'🚫 BLOCKED' if memory_percent > 95 else '✅ OK'}")
        
    except Exception as e:
        print(f"   ❌ Error testing memory monitoring: {e}")
    
    # Check if we're in a container
    print(f"\n🐳 Container Detection:")
    try:
        with open('/proc/1/cgroup', 'r') as f:
            cgroup_info = f.read()
            if 'docker' in cgroup_info or 'containerd' in cgroup_info:
                print("   ✅ Running in container")
            else:
                print("   ❌ Not running in container")
    except:
        print("   ❓ Cannot determine container status")

if __name__ == "__main__":
    test_memory_monitoring()
