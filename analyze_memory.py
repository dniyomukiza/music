#!/usr/bin/env python3
"""
Memory analysis script for the music application.
This script analyzes memory usage patterns and identifies potential leaks.
"""

import psutil
import os
import gc
import sys
import tracemalloc
from datetime import datetime
import json

class MemoryAnalyzer:
    def __init__(self):
        self.start_time = datetime.now()
        self.memory_snapshots = []
        
    def get_memory_info(self):
        """Get detailed memory information."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'process_memory_mb': memory_info.rss / 1024 / 1024,
                'process_memory_percent': process.memory_percent(),
                'system_memory_percent': system_memory.percent,
                'system_memory_used_mb': system_memory.used / 1024 / 1024,
                'system_memory_available_mb': system_memory.available / 1024 / 1024,
                'gc_counts': gc.get_count(),
                'gc_stats': gc.get_stats()
            }
        except Exception as e:
            print(f"Error getting memory info: {e}")
            return None
    
    def analyze_memory_objects(self):
        """Analyze memory objects to find potential leaks."""
        print("🔍 Analyzing memory objects...")
        
        # Get all objects in memory
        objects = gc.get_objects()
        object_counts = {}
        object_sizes = {}
        
        for obj in objects:
            obj_type = type(obj).__name__
            object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
            
            try:
                obj_size = sys.getsizeof(obj)
                object_sizes[obj_type] = object_sizes.get(obj_type, 0) + obj_size
            except:
                pass
        
        # Sort by count and size
        top_objects_by_count = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        top_objects_by_size = sorted(object_sizes.items(), key=lambda x: x[1], reverse=True)[:20]
        
        print("\n📊 Top objects by count:")
        for obj_type, count in top_objects_by_count:
            print(f"  {obj_type}: {count:,} objects")
        
        print("\n💾 Top objects by memory usage:")
        for obj_type, size in top_objects_by_size:
            print(f"  {obj_type}: {size / 1024 / 1024:.1f} MB")
        
        return {
            'object_counts': dict(top_objects_by_count),
            'object_sizes': {k: v / 1024 / 1024 for k, v in top_objects_by_size}
        }
    
    def check_memory_leaks(self):
        """Check for potential memory leaks."""
        print("🔍 Checking for memory leaks...")
        
        # Check for circular references
        circular_refs = gc.garbage
        if circular_refs:
            print(f"⚠️  Found {len(circular_refs)} circular references in garbage")
            for i, obj in enumerate(circular_refs[:5]):  # Show first 5
                print(f"  {i+1}. {type(obj).__name__}: {obj}")
        else:
            print("✅ No circular references found")
        
        # Check for uncollectable objects
        uncollectable = len(gc.garbage)
        if uncollectable > 0:
            print(f"⚠️  Found {uncollectable} uncollectable objects")
        else:
            print("✅ No uncollectable objects found")
        
        # Check for large objects
        large_objects = []
        for obj in gc.get_objects():
            try:
                size = sys.getsizeof(obj)
                if size > 1024 * 1024:  # > 1MB
                    large_objects.append((type(obj).__name__, size))
            except:
                pass
        
        if large_objects:
            print(f"⚠️  Found {len(large_objects)} large objects (>1MB):")
            for obj_type, size in sorted(large_objects, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {obj_type}: {size / 1024 / 1024:.1f} MB")
        else:
            print("✅ No large objects found")
        
        return {
            'circular_refs': len(circular_refs),
            'uncollectable': uncollectable,
            'large_objects': len(large_objects)
        }
    
    def analyze_memory_patterns(self):
        """Analyze memory usage patterns over time."""
        print("📈 Analyzing memory patterns...")
        
        # Read memory usage log if it exists
        memory_log = []
        try:
            with open('memory_usage.log', 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        memory_log.append({
                            'timestamp': parts[0],
                            'phase': parts[1],
                            'percent': float(parts[2]),
                            'used_mb': float(parts[3])
                        })
        except FileNotFoundError:
            print("No memory usage log found")
            return None
        
        if not memory_log:
            print("No memory usage data found")
            return None
        
        # Analyze patterns
        phases = {}
        for entry in memory_log:
            phase = entry['phase']
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(entry['percent'])
        
        print("\n📊 Memory usage by phase:")
        for phase, percentages in phases.items():
            avg_percent = sum(percentages) / len(percentages)
            max_percent = max(percentages)
            min_percent = min(percentages)
            print(f"  {phase}: avg={avg_percent:.1f}%, max={max_percent:.1f}%, min={min_percent:.1f}%")
        
        return phases
    
    def generate_recommendations(self, analysis_results):
        """Generate recommendations based on analysis."""
        print("\n💡 Recommendations:")
        
        recommendations = []
        
        # Check memory usage
        mem_info = self.get_memory_info()
        if mem_info and mem_info['system_memory_percent'] > 80:
            recommendations.append("🚨 High memory usage detected - consider restarting the application")
        
        # Check for memory leaks
        if analysis_results.get('circular_refs', 0) > 0:
            recommendations.append("🔧 Circular references found - check for memory leaks in code")
        
        if analysis_results.get('uncollectable', 0) > 0:
            recommendations.append("🧹 Uncollectable objects found - review object lifecycle management")
        
        if analysis_results.get('large_objects', 0) > 0:
            recommendations.append("📦 Large objects detected - consider optimizing data structures")
        
        # Check object counts
        object_counts = analysis_results.get('object_counts', {})
        if object_counts.get('dict', 0) > 10000:
            recommendations.append("📚 High dictionary count - check for cache accumulation")
        
        if object_counts.get('list', 0) > 10000:
            recommendations.append("📋 High list count - check for list accumulation")
        
        if not recommendations:
            recommendations.append("✅ Memory usage appears normal")
        
        for rec in recommendations:
            print(f"  {rec}")
        
        return recommendations
    
    def run_analysis(self):
        """Run complete memory analysis."""
        print("🔍 Memory Analysis Starting...")
        print("=" * 50)
        
        # Get current memory info
        mem_info = self.get_memory_info()
        if mem_info:
            print(f"📊 Current Memory Usage:")
            print(f"  Process: {mem_info['process_memory_mb']:.1f} MB ({mem_info['process_memory_percent']:.1f}%)")
            print(f"  System: {mem_info['system_memory_used_mb']:.1f} MB ({mem_info['system_memory_percent']:.1f}%)")
            print(f"  Available: {mem_info['system_memory_available_mb']:.1f} MB")
        
        # Analyze objects
        object_analysis = self.analyze_memory_objects()
        
        # Check for leaks
        leak_analysis = self.check_memory_leaks()
        
        # Analyze patterns
        pattern_analysis = self.analyze_memory_patterns()
        
        # Generate recommendations
        all_analysis = {
            'object_counts': object_analysis.get('object_counts', {}),
            'object_sizes': object_analysis.get('object_sizes', {}),
            'circular_refs': leak_analysis.get('circular_refs', 0),
            'uncollectable': leak_analysis.get('uncollectable', 0),
            'large_objects': leak_analysis.get('large_objects', 0)
        }
        
        recommendations = self.generate_recommendations(all_analysis)
        
        # Save analysis results
        analysis_report = {
            'timestamp': datetime.now().isoformat(),
            'memory_info': mem_info,
            'object_analysis': object_analysis,
            'leak_analysis': leak_analysis,
            'pattern_analysis': pattern_analysis,
            'recommendations': recommendations
        }
        
        try:
            with open('memory_analysis_report.json', 'w') as f:
                json.dump(analysis_report, f, indent=2)
            print(f"\n📄 Analysis report saved to memory_analysis_report.json")
        except Exception as e:
            print(f"⚠️  Could not save analysis report: {e}")
        
        print("\n✅ Memory analysis complete!")

def main():
    analyzer = MemoryAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()

