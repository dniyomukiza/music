#!/usr/bin/env python3
"""
Application restart script with memory monitoring.
This script can be used to restart the application when memory usage gets too high.
"""

import subprocess
import time
import psutil
import os
import signal

def find_app_processes():
    """Find running application processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'python' in cmdline and ('run.py' in cmdline or 'gunicorn' in cmdline):
                    processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def get_memory_usage():
    """Get total memory usage of application processes."""
    processes = find_app_processes()
    total_memory = 0
    for proc in processes:
        try:
            total_memory += proc.memory_info().rss / 1024 / 1024  # MB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total_memory, len(processes)

def restart_application():
    """Restart the application."""
    print("🔄 Restarting application...")
    
    # Find and kill existing processes
    processes = find_app_processes()
    for proc in processes:
        try:
            print(f"🛑 Stopping process {proc.pid}")
            proc.terminate()
            proc.wait(timeout=10)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    # Wait a moment
    time.sleep(2)
    
    # Start the application
    print("🚀 Starting application...")
    try:
        subprocess.Popen(['python', 'run.py'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        print("✅ Application started successfully")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def monitor_and_restart(memory_threshold=200, check_interval=30):
    """Monitor memory usage and restart if threshold is exceeded."""
    print(f"🔍 Monitoring application memory usage (threshold: {memory_threshold}MB)")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            memory_usage, process_count = get_memory_usage()
            
            if process_count > 0:
                print(f"📊 Memory usage: {memory_usage:.1f}MB ({process_count} processes)")
                
                if memory_usage > memory_threshold:
                    print(f"⚠️  Memory usage exceeded threshold ({memory_threshold}MB)")
                    restart_application()
                    time.sleep(10)  # Wait before next check
                else:
                    print("✅ Memory usage is within limits")
            else:
                print("❌ No application processes found")
                restart_application()
                time.sleep(10)
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "restart":
            restart_application()
        elif sys.argv[1] == "monitor":
            threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 200
            monitor_and_restart(threshold)
        else:
            print("Usage: python restart_app.py [restart|monitor] [threshold_mb]")
    else:
        # Default: just restart
        restart_application()
