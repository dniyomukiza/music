#!/usr/bin/env python3
"""
Advanced memory monitoring script for the music application.
This script monitors memory usage and can restart the application if needed.
"""

import psutil
import os
import time
import sys
import subprocess
import signal
import json
from datetime import datetime

class MemoryMonitor:
    def __init__(self, memory_threshold=85, check_interval=10, restart_threshold=95):
        self.memory_threshold = memory_threshold
        self.restart_threshold = restart_threshold
        self.check_interval = check_interval
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_cooldown = 300  # 5 minutes
        self.last_restart = 0
        
    def get_memory_info(self):
        """Get current memory usage information."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # Get system memory info
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
    
    def check_container_limits(self):
        """Check if running in a container and get memory limits."""
        try:
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                limit_bytes = int(f.read().strip())
                return limit_bytes / 1024 / 1024 / 1024  # Convert to GB
        except:
            return None
    
    def force_garbage_collection(self):
        """Force garbage collection to free memory."""
        try:
            import gc
            print("🧹 Forcing garbage collection...")
            gc.collect()
            gc.collect()  # Call twice for better cleanup
            
            # Try to trim memory on Linux
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                print("✅ Memory trimmed successfully")
            except:
                print("⚠️  Memory trim not available on this system")
                
        except Exception as e:
            print(f"❌ Error during garbage collection: {e}")
    
    def restart_application(self):
        """Restart the application if memory usage is too high."""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_restart < self.restart_cooldown:
            print(f"⏳ Restart cooldown active. Next restart allowed in {self.restart_cooldown - (current_time - self.last_restart):.0f} seconds")
            return False
        
        # Check max restarts
        if self.restart_count >= self.max_restarts:
            print(f"🚨 Maximum restart limit reached ({self.max_restarts}). Manual intervention required.")
            return False
        
        try:
            print("🔄 Restarting application...")
            
            # Try to restart using docker-compose
            result = subprocess.run(['docker-compose', 'restart', 'app'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.restart_count += 1
                self.last_restart = current_time
                print(f"✅ Application restarted successfully (restart #{self.restart_count})")
                return True
            else:
                print(f"❌ Failed to restart application: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Restart timeout - application may be unresponsive")
            return False
        except Exception as e:
            print(f"❌ Error restarting application: {e}")
            return False
    
    def log_memory_status(self, mem_info):
        """Log memory status to file."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'process_memory_mb': mem_info['process_memory_mb'],
                'process_memory_percent': mem_info['process_memory_percent'],
                'system_memory_percent': mem_info['system_memory_used_percent'],
                'system_memory_used_mb': mem_info['system_memory_used_mb'],
                'system_memory_available_mb': mem_info['system_memory_available_gb'] * 1024
            }
            
            with open('memory_monitor.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not log memory status: {e}")
    
    def monitor(self, duration_seconds=None):
        """Monitor memory usage for a specified duration or indefinitely."""
        print("🔍 Advanced Memory Monitor Starting...")
        print("=" * 60)
        
        container_limit = self.check_container_limits()
        if container_limit:
            print(f"📦 Container Memory Limit: {container_limit:.2f} GB")
        else:
            print("🖥️  Running on host system")
        
        print(f"⏱️  Monitoring every {self.check_interval} seconds")
        print(f"⚠️  Warning threshold: {self.memory_threshold}%")
        print(f"🚨 Restart threshold: {self.restart_threshold}%")
        print("=" * 60)
        
        start_time = time.time()
        max_memory = 0
        warning_count = 0
        
        try:
            while True:
                mem_info = self.get_memory_info()
                if not mem_info:
                    print("❌ Could not get memory information")
                    time.sleep(self.check_interval)
                    continue
                
                max_memory = max(max_memory, mem_info['process_memory_mb'])
                
                # Log memory status
                self.log_memory_status(mem_info)
                
                # Check memory usage
                system_memory_percent = mem_info['system_memory_used_percent']
                process_memory_mb = mem_info['process_memory_mb']
                
                status_icon = "🟢"
                if system_memory_percent > self.restart_threshold:
                    status_icon = "🔴"
                elif system_memory_percent > self.memory_threshold:
                    status_icon = "🟡"
                
                print(f"{status_icon} {datetime.now().strftime('%H:%M:%S')} | "
                      f"Process: {process_memory_mb:.1f}MB | "
                      f"System: {system_memory_percent:.1f}% used | "
                      f"Available: {mem_info['system_memory_available_gb']:.1f}GB")
                
                # Handle high memory usage
                if system_memory_percent > self.restart_threshold:
                    print(f"🚨 CRITICAL: Memory usage {system_memory_percent:.1f}% exceeds restart threshold!")
                    
                    # Force garbage collection first
                    self.force_garbage_collection()
                    
                    # Check memory again after cleanup
                    time.sleep(2)
                    mem_info_after = self.get_memory_info()
                    if mem_info_after and mem_info_after['system_memory_used_percent'] > self.restart_threshold:
                        print("🔄 Memory still high after cleanup, attempting restart...")
                        if self.restart_application():
                            print("✅ Restart initiated, waiting for application to stabilize...")
                            time.sleep(30)  # Wait for restart to complete
                        else:
                            print("❌ Restart failed, continuing monitoring...")
                    else:
                        print("✅ Memory usage reduced after cleanup")
                        
                elif system_memory_percent > self.memory_threshold:
                    warning_count += 1
                    print(f"⚠️  WARNING: High memory usage detected ({system_memory_percent:.1f}%) - count: {warning_count}")
                    
                    # Force garbage collection on high memory
                    if warning_count % 3 == 0:  # Every 3rd warning
                        self.force_garbage_collection()
                else:
                    warning_count = 0  # Reset warning count
                
                # Check if duration limit reached
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        finally:
            print("=" * 60)
            print(f"📈 Peak Memory Usage: {max_memory:.1f} MB")
            print(f"🔄 Total Restarts: {self.restart_count}")
            
            # Recommendations
            print("\n💡 Recommendations:")
            if max_memory > 200:
                print("   - Consider reducing worker count in gunicorn.conf.py")
                print("   - Enable more aggressive garbage collection")
                print("   - Check for memory leaks in news generation")
            
            if container_limit and max_memory > container_limit * 1024 * 0.7:
                print("   - Increase container memory limit")
                print("   - Optimize memory-intensive operations")
                print("   - Consider using external services for heavy processing")

def main():
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Usage: python memory_monitor_advanced.py [duration_seconds]")
            sys.exit(1)
    else:
        duration = None
    
    monitor = MemoryMonitor(
        memory_threshold=85,  # Warning at 85%
        restart_threshold=95,  # Restart at 95%
        check_interval=10     # Check every 10 seconds
    )
    
    monitor.monitor(duration)

if __name__ == "__main__":
    main()

