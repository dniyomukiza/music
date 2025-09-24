#!/usr/bin/env python3
"""
Emergency memory debugging script for the music application.
This script helps identify what's causing memory leaks and provides emergency fixes.
"""

import psutil
import os
import time
import sys
import subprocess
import signal
import json
import gc
from datetime import datetime

class EmergencyMemoryDebugger:
    def __init__(self):
        self.check_interval = 2  # Check every 2 seconds
        self.emergency_threshold = 60  # Emergency at 60% memory usage
        
    def get_detailed_memory_info(self):
        """Get detailed memory usage information."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            # Get memory maps
            memory_maps = process.memory_maps()
            
            return {
                'process_memory_mb': memory_info.rss / 1024 / 1024,
                'process_memory_percent': process.memory_percent(),
                'process_vms_mb': memory_info.vms / 1024 / 1024,
                'system_memory_total_gb': system_memory.total / 1024 / 1024 / 1024,
                'system_memory_available_gb': system_memory.available / 1024 / 1024 / 1024,
                'system_memory_used_percent': system_memory.percent,
                'system_memory_used_mb': system_memory.used / 1024 / 1024,
                'memory_maps_count': len(memory_maps),
                'gc_counts': gc.get_count()
            }
        except Exception as e:
            print(f"Error getting memory info: {e}")
            return None
    
    def emergency_garbage_collection(self):
        """Emergency garbage collection with detailed reporting."""
        try:
            print("🚨 EMERGENCY GARBAGE COLLECTION")
            print("=" * 50)
            
            # Get GC stats before
            gc_before = gc.get_count()
            print(f"GC Counts Before: {gc_before}")
            
            # Force multiple garbage collections
            for i in range(5):
                collected = gc.collect()
                print(f"GC Pass {i+1}: Collected {collected} objects")
            
            # Get GC stats after
            gc_after = gc.get_count()
            print(f"GC Counts After: {gc_after}")
            
            # Try to trim memory on Linux
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                result = libc.malloc_trim(0)
                print(f"Memory trim result: {result}")
            except Exception as e:
                print(f"Memory trim failed: {e}")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error during emergency garbage collection: {e}")
    
    def check_docker_memory_usage(self):
        """Check Docker container memory usage."""
        try:
            result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 
                                   'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("🐳 Docker Container Memory Usage:")
                print(result.stdout)
            else:
                print(f"❌ Failed to get Docker stats: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error checking Docker memory: {e}")
    
    def emergency_restart_services(self):
        """Emergency restart of all services."""
        try:
            print("🚨 EMERGENCY SERVICE RESTART")
            print("=" * 50)
            
            services = ['app', 'fastapi', 'liquidsoap', 'icecast2']
            
            for service in services:
                print(f"Restarting {service}...")
                result = subprocess.run(['docker-compose', 'restart', service], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"✅ {service} restarted successfully")
                else:
                    print(f"❌ Failed to restart {service}: {result.stderr}")
                
                time.sleep(5)  # Wait between restarts
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error during emergency restart: {e}")
    
    def log_memory_debug_info(self, mem_info):
        """Log detailed memory debug information."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'process_memory_mb': mem_info['process_memory_mb'],
                'process_memory_percent': mem_info['process_memory_percent'],
                'process_vms_mb': mem_info['process_vms_mb'],
                'system_memory_percent': mem_info['system_memory_used_percent'],
                'system_memory_used_mb': mem_info['system_memory_used_mb'],
                'system_memory_available_mb': mem_info['system_memory_available_gb'] * 1024,
                'memory_maps_count': mem_info['memory_maps_count'],
                'gc_counts': mem_info['gc_counts']
            }
            
            with open('emergency_memory_debug.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not log memory debug info: {e}")
    
    def monitor_and_debug(self, duration_seconds=None):
        """Monitor memory usage and provide emergency debugging."""
        print("🚨 EMERGENCY MEMORY DEBUGGER STARTING")
        print("=" * 60)
        print("This script will help identify memory leaks and provide emergency fixes")
        print("=" * 60)
        
        start_time = time.time()
        max_memory = 0
        emergency_count = 0
        
        try:
            while True:
                mem_info = self.get_detailed_memory_info()
                if not mem_info:
                    print("❌ Could not get memory information")
                    time.sleep(self.check_interval)
                    continue
                
                max_memory = max(max_memory, mem_info['process_memory_mb'])
                
                # Log memory debug info
                self.log_memory_debug_info(mem_info)
                
                # Check memory usage
                system_memory_percent = mem_info['system_memory_used_percent']
                process_memory_mb = mem_info['process_memory_mb']
                
                status_icon = "🟢"
                if system_memory_percent > self.emergency_threshold:
                    status_icon = "🔴"
                    emergency_count += 1
                elif system_memory_percent > 50:
                    status_icon = "🟡"
                
                print(f"{status_icon} {datetime.now().strftime('%H:%M:%S')} | "
                      f"Process: {process_memory_mb:.1f}MB | "
                      f"System: {system_memory_percent:.1f}% used | "
                      f"Maps: {mem_info['memory_maps_count']} | "
                      f"GC: {mem_info['gc_counts']}")
                
                # Emergency actions
                if system_memory_percent > self.emergency_threshold:
                    print(f"🚨 EMERGENCY: Memory usage {system_memory_percent:.1f}% exceeds threshold!")
                    
                    # Emergency garbage collection
                    self.emergency_garbage_collection()
                    
                    # Check Docker memory usage
                    self.check_docker_memory_usage()
                    
                    # Emergency restart if this is the 3rd emergency
                    if emergency_count >= 3:
                        print("🚨 Multiple emergencies detected, restarting services...")
                        self.emergency_restart_services()
                        emergency_count = 0  # Reset counter
                    
                    time.sleep(10)  # Wait longer after emergency actions
                else:
                    emergency_count = 0  # Reset counter
                
                # Check if duration limit reached
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Emergency debugging stopped by user")
        except Exception as e:
            print(f"\n❌ Emergency debugging error: {e}")
        finally:
            print("=" * 60)
            print(f"📈 Peak Memory Usage: {max_memory:.1f} MB")
            print(f"🚨 Emergency Events: {emergency_count}")
            
            # Final recommendations
            print("\n💡 EMERGENCY RECOMMENDATIONS:")
            print("   1. Check application logs for memory leaks")
            print("   2. Consider reducing worker count to 1")
            print("   3. Implement request-level memory monitoring")
            print("   4. Consider using external services for heavy processing")
            print("   5. Review application code for memory leaks")

def main():
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Usage: python emergency_memory_debug.py [duration_seconds]")
            sys.exit(1)
    else:
        duration = None
    
    debugger = EmergencyMemoryDebugger()
    debugger.monitor_and_debug(duration)

if __name__ == "__main__":
    main()
