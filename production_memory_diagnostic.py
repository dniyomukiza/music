#!/usr/bin/env python3
"""
Production Memory Diagnostic Script
This script helps diagnose memory issues in production Linux environments.
"""

import psutil
import os
import subprocess
import json
from datetime import datetime

def get_host_memory_info():
    """Get detailed host system memory information."""
    try:
        # System memory
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Memory per process
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['memory_percent'] > 1.0:  # Only processes using >1% memory
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'memory_mb': proc_info['memory_info'].rss / 1024 / 1024,
                        'memory_percent': proc_info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        
        return {
            'system_memory': {
                'total_gb': memory.total / 1024 / 1024 / 1024,
                'available_gb': memory.available / 1024 / 1024 / 1024,
                'used_gb': memory.used / 1024 / 1024 / 1024,
                'percent_used': memory.percent,
                'free_gb': memory.free / 1024 / 1024 / 1024
            },
            'swap_memory': {
                'total_gb': swap.total / 1024 / 1024 / 1024,
                'used_gb': swap.used / 1024 / 1024 / 1024,
                'percent_used': swap.percent,
                'free_gb': swap.free / 1024 / 1024 / 1024
            },
            'top_processes': processes[:10]  # Top 10 memory consumers
        }
    except Exception as e:
        return {'error': str(e)}

def get_docker_memory_info():
    """Get Docker container memory information."""
    try:
        # Get Docker stats
        result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 'json'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container_data = json.loads(line)
                        containers.append({
                            'name': container_data.get('Name', 'Unknown'),
                            'cpu_percent': container_data.get('CPUPerc', '0%'),
                            'memory_usage': container_data.get('MemUsage', '0B'),
                            'memory_percent': container_data.get('MemPerc', '0%'),
                            'memory_limit': container_data.get('MemLimit', '0B')
                        })
                    except json.JSONDecodeError:
                        continue
            
            return {'containers': containers}
        else:
            return {'error': f'Docker stats failed: {result.stderr}'}
            
    except subprocess.TimeoutExpired:
        return {'error': 'Docker stats command timed out'}
    except FileNotFoundError:
        return {'error': 'Docker command not found'}
    except Exception as e:
        return {'error': str(e)}

def get_container_limits():
    """Get container memory limits from cgroups."""
    try:
        # Check if we're in a container
        if os.path.exists('/sys/fs/cgroup/memory/memory.limit_in_bytes'):
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                limit_bytes = int(f.read().strip())
                return {
                    'container_limit_gb': limit_bytes / 1024 / 1024 / 1024,
                    'container_limit_mb': limit_bytes / 1024 / 1024,
                    'is_containerized': True
                }
        else:
            return {'is_containerized': False}
    except Exception as e:
        return {'error': str(e)}

def check_memory_pressure():
    """Check for memory pressure indicators."""
    try:
        # Check /proc/meminfo for memory pressure
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    meminfo[key.strip()] = value.strip()
        
        # Check for OOM killer activity
        oom_kills = 0
        try:
            with open('/var/log/kern.log', 'r') as f:
                for line in f:
                    if 'Out of memory' in line or 'oom-killer' in line:
                        oom_kills += 1
        except FileNotFoundError:
            # Try alternative log locations
            for log_file in ['/var/log/messages', '/var/log/syslog']:
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if 'Out of memory' in line or 'oom-killer' in line:
                                oom_kills += 1
                    break
                except FileNotFoundError:
                    continue
        
        return {
            'meminfo': meminfo,
            'oom_kills': oom_kills,
            'memory_pressure': meminfo.get('MemAvailable', '0 kB') if 'MemAvailable' in meminfo else 'Unknown'
        }
    except Exception as e:
        return {'error': str(e)}

def generate_diagnostic_report():
    """Generate a comprehensive memory diagnostic report."""
    print("🔍 Production Memory Diagnostic Report")
    print("=" * 60)
    print(f"📅 Generated: {datetime.now().isoformat()}")
    print()
    
    # Host memory info
    print("🖥️  HOST SYSTEM MEMORY")
    print("-" * 30)
    host_info = get_host_memory_info()
    if 'error' in host_info:
        print(f"❌ Error getting host memory info: {host_info['error']}")
    else:
        sys_mem = host_info['system_memory']
        swap_mem = host_info['swap_memory']
        
        print(f"📊 Total Memory: {sys_mem['total_gb']:.2f} GB")
        print(f"📊 Used Memory: {sys_mem['used_gb']:.2f} GB ({sys_mem['percent_used']:.1f}%)")
        print(f"📊 Available Memory: {sys_mem['available_gb']:.2f} GB")
        print(f"📊 Free Memory: {sys_mem['free_gb']:.2f} GB")
        print()
        print(f"💾 Swap Total: {swap_mem['total_gb']:.2f} GB")
        print(f"💾 Swap Used: {swap_mem['used_gb']:.2f} GB ({swap_mem['percent_used']:.1f}%)")
        print()
        
        # Memory status
        if sys_mem['percent_used'] > 90:
            print("🚨 CRITICAL: Host memory usage > 90%")
        elif sys_mem['percent_used'] > 80:
            print("⚠️  WARNING: Host memory usage > 80%")
        elif sys_mem['percent_used'] > 70:
            print("🟡 CAUTION: Host memory usage > 70%")
        else:
            print("✅ Host memory usage is normal")
        
        print()
        print("🔝 TOP MEMORY CONSUMING PROCESSES:")
        for i, proc in enumerate(host_info['top_processes'][:5], 1):
            print(f"   {i}. {proc['name']} (PID {proc['pid']}): {proc['memory_mb']:.1f} MB ({proc['memory_percent']:.1f}%)")
    
    print()
    
    # Docker info
    print("🐳 DOCKER CONTAINER MEMORY")
    print("-" * 30)
    docker_info = get_docker_memory_info()
    if 'error' in docker_info:
        print(f"❌ Error getting Docker info: {docker_info['error']}")
    else:
        if docker_info['containers']:
            for container in docker_info['containers']:
                print(f"📦 {container['name']}:")
                print(f"   Memory Usage: {container['memory_usage']}")
                print(f"   Memory Limit: {container['memory_limit']}")
                print(f"   Memory Percent: {container['memory_percent']}")
                print()
        else:
            print("ℹ️  No Docker containers found")
    
    # Container limits
    print("📦 CONTAINER LIMITS")
    print("-" * 20)
    container_limits = get_container_limits()
    if 'error' in container_limits:
        print(f"❌ Error getting container limits: {container_limits['error']}")
    else:
        if container_limits.get('is_containerized'):
            print(f"✅ Running in container")
            print(f"📊 Container Memory Limit: {container_limits['container_limit_gb']:.2f} GB")
            print(f"📊 Container Memory Limit: {container_limits['container_limit_mb']:.0f} MB")
        else:
            print("ℹ️  Running on host system (not containerized)")
    
    print()
    
    # Memory pressure
    print("⚡ MEMORY PRESSURE INDICATORS")
    print("-" * 35)
    pressure_info = check_memory_pressure()
    if 'error' in pressure_info:
        print(f"❌ Error checking memory pressure: {pressure_info['error']}")
    else:
        print(f"📊 Available Memory: {pressure_info.get('memory_pressure', 'Unknown')}")
        print(f"🚨 OOM Kills Detected: {pressure_info.get('oom_kills', 0)}")
        
        if pressure_info.get('oom_kills', 0) > 0:
            print("🚨 WARNING: Out-of-memory kills detected!")
    
    print()
    print("💡 RECOMMENDATIONS")
    print("-" * 20)
    
    # Generate recommendations based on findings
    if 'system_memory' in host_info:
        sys_mem = host_info['system_memory']
        if sys_mem['percent_used'] > 80:
            print("🔧 HOST MEMORY RECOMMENDATIONS:")
            print("   - Consider upgrading server RAM")
            print("   - Optimize other services running on the host")
            print("   - Enable swap if not already enabled")
            print("   - Monitor for memory leaks in other applications")
        
        if sys_mem['percent_used'] > 70:
            print("🔧 CONTAINER RECOMMENDATIONS:")
            print("   - Increase Docker container memory limits")
            print("   - Optimize application memory usage")
            print("   - Consider reducing concurrent operations")
            print("   - Implement more aggressive garbage collection")
    
    print("🔧 NEWS GENERATION SPECIFIC:")
    print("   - Reduce number of topics per generation")
    print("   - Implement memory monitoring during generation")
    print("   - Add memory cleanup between generations")
    print("   - Consider external AI service for heavy operations")

if __name__ == "__main__":
    generate_diagnostic_report()

