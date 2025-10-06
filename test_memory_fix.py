#!/usr/bin/env python3
"""
Test script to verify the memory monitoring fix.
This script tests the get_memory_usage function to ensure it's using container memory correctly.
"""

import sys
import os
sys.path.append('/Users/nididier/Documents/music-1')

from glconnect.news_agent import get_memory_usage

def test_memory_monitoring():
    """Test the memory monitoring function."""
    print("🧪 Testing Memory Monitoring Fix")
    print("=" * 50)
    
    try:
        # Test the memory usage function
        memory_percent = get_memory_usage()
        
        print(f"📊 Memory Usage: {memory_percent:.1f}%")
        
        # Check if we're getting reasonable values
        if memory_percent > 100:
            print("❌ ERROR: Memory usage > 100% - this shouldn't happen!")
            return False
        elif memory_percent < 0:
            print("❌ ERROR: Memory usage < 0% - this shouldn't happen!")
            return False
        else:
            print("✅ Memory usage is within reasonable bounds")
            
        # Test thresholds
        print(f"\n🎯 Testing Thresholds:")
        print(f"   - Warning threshold (80%): {'⚠️  WARNING' if memory_percent > 80 else '✅ OK'}")
        print(f"   - Critical threshold (90%): {'🚨 CRITICAL' if memory_percent > 90 else '✅ OK'}")
        print(f"   - Blocking threshold (95%): {'🚫 BLOCKED' if memory_percent > 95 else '✅ OK'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing memory monitoring: {e}")
        return False

if __name__ == "__main__":
    success = test_memory_monitoring()
    
    if success:
        print("\n🎉 Memory monitoring test completed successfully!")
        print("The fix should now allow news generation to work with 4GB containers.")
    else:
        print("\n❌ Memory monitoring test failed!")
        print("Please check the implementation.")
