#!/usr/bin/env python3
"""
Memory Monitoring Script for Ink Studio
Monitors memory usage and provides optimization recommendations
"""

import psutil
import time
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Monitor memory usage and provide optimization recommendations"""
    
    def __init__(self, threshold_percent=80):
        self.threshold_percent = threshold_percent
        self.start_time = time.time()
        self.peak_memory = 0
        self.memory_samples = []
    
    def get_system_memory(self):
        """Get system memory information"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent,
            'free': memory.free
        }
    
    def get_process_memory(self, process_name='python'):
        """Get memory usage for specific processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent']):
            try:
                if process_name in proc.info['name'].lower():
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'memory_percent': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    
    def check_memory_health(self):
        """Check overall memory health"""
        system_memory = self.get_system_memory()
        python_processes = self.get_process_memory('python')
        
        # Update peak memory
        if system_memory['percent'] > self.peak_memory:
            self.peak_memory = system_memory['percent']
        
        # Store sample
        self.memory_samples.append({
            'timestamp': datetime.now(),
            'system_percent': system_memory['percent'],
            'python_processes': python_processes
        })
        
        # Keep only last 100 samples
        if len(self.memory_samples) > 100:
            self.memory_samples = self.memory_samples[-100:]
        
        # Check thresholds
        warnings = []
        if system_memory['percent'] > self.threshold_percent:
            warnings.append(f"High system memory usage: {system_memory['percent']:.1f}%")
        
        total_python_memory = sum(p['memory_mb'] for p in python_processes)
        if total_python_memory > 500:  # More than 500MB
            warnings.append(f"High Python process memory: {total_python_memory:.1f}MB")
        
        return {
            'system_memory': system_memory,
            'python_processes': python_processes,
            'warnings': warnings,
            'peak_memory': self.peak_memory
        }
    
    def get_optimization_recommendations(self):
        """Get optimization recommendations based on memory usage"""
        recommendations = []
        
        if self.peak_memory > 90:
            recommendations.append("CRITICAL: Memory usage exceeded 90%. Consider:")
            recommendations.append("  - Restarting the application")
            recommendations.append("  - Implementing database connection pooling")
            recommendations.append("  - Adding memory caching with Redis")
            recommendations.append("  - Optimizing database queries")
        
        elif self.peak_memory > 80:
            recommendations.append("WARNING: High memory usage detected. Consider:")
            recommendations.append("  - Implementing query result caching")
            recommendations.append("  - Optimizing image loading (lazy loading)")
            recommendations.append("  - Adding database indexes")
            recommendations.append("  - Implementing pagination for large datasets")
        
        elif self.peak_memory > 70:
            recommendations.append("INFO: Moderate memory usage. Monitor for:")
            recommendations.append("  - Memory leaks in long-running processes")
            recommendations.append("  - Inefficient database queries")
            recommendations.append("  - Large file uploads")
        
        return recommendations
    
    def generate_report(self):
        """Generate a comprehensive memory report"""
        health = self.check_memory_health()
        recommendations = self.get_optimization_recommendations()
        
        report = f"""
=== Ink Studio Memory Report ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Uptime: {time.time() - self.start_time:.1f} seconds

System Memory:
  Total: {health['system_memory']['total'] / 1024 / 1024 / 1024:.1f} GB
  Used: {health['system_memory']['used'] / 1024 / 1024 / 1024:.1f} GB
  Available: {health['system_memory']['available'] / 1024 / 1024 / 1024:.1f} GB
  Usage: {health['system_memory']['percent']:.1f}%
  Peak Usage: {self.peak_memory:.1f}%

Python Processes:
"""
        
        for proc in health['python_processes']:
            report += f"  PID {proc['pid']}: {proc['memory_mb']:.1f} MB ({proc['memory_percent']:.1f}%)\n"
        
        if health['warnings']:
            report += "\nWarnings:\n"
            for warning in health['warnings']:
                report += f"  - {warning}\n"
        
        if recommendations:
            report += "\nRecommendations:\n"
            for rec in recommendations:
                report += f"  {rec}\n"
        
        return report
    
    def monitor_continuously(self, interval=30):
        """Monitor memory continuously"""
        logger.info("Starting continuous memory monitoring...")
        
        try:
            while True:
                health = self.check_memory_health()
                
                if health['warnings']:
                    logger.warning(f"Memory warnings: {', '.join(health['warnings'])}")
                
                logger.info(f"Memory: {health['system_memory']['percent']:.1f}% "
                           f"(Peak: {self.peak_memory:.1f}%)")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Memory monitoring stopped by user")
            print(self.generate_report())

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'report':
            monitor = MemoryMonitor()
            print(monitor.generate_report())
        elif sys.argv[1] == 'monitor':
            monitor = MemoryMonitor()
            monitor.monitor_continuously()
        else:
            print("Usage: python memory_monitor.py [report|monitor]")
    else:
        # Default: generate report
        monitor = MemoryMonitor()
        print(monitor.generate_report())

if __name__ == '__main__':
    main()