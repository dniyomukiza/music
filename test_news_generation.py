#!/usr/bin/env python3
"""
Test script for news generation debugging.
This script helps identify issues with news generation.
"""

import sys
import os
import traceback
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_news_generation():
    """Test news generation with detailed error reporting."""
    print("🧪 Testing News Generation")
    print("=" * 50)
    
    try:
        # Import the news generation function
        from glconnect.news_agent import generate_broadcast
        print("✅ Successfully imported generate_broadcast function")
        
        # Test with a simple topic
        test_topics = ["Technology advances in 2024"]
        print(f"📝 Testing with topics: {test_topics}")
        
        # Generate broadcast
        print("🚀 Starting news generation...")
        result = generate_broadcast(test_topics, max_retries=1, task_id="test-123")
        
        if result:
            print("✅ News generation completed!")
            print(f"📊 Result keys: {list(result.keys())}")
            print(f"🎵 Audio file: {result.get('audio_file', 'None')}")
            print(f"📄 Summary: {result.get('summary', 'None')[:200]}...")
            if 'error' in result:
                print(f"❌ Error in result: {result['error']}")
        else:
            print("❌ News generation returned None")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root directory")
    except Exception as e:
        print(f"❌ Error during news generation: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"📋 Traceback:")
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

def test_memory_usage():
    """Test memory usage during news generation."""
    print("\n🧠 Testing Memory Usage")
    print("=" * 50)
    
    try:
        import psutil
        import gc
        
        # Get initial memory
        memory_before = psutil.virtual_memory()
        print(f"📊 Memory before: {memory_before.used / 1024 / 1024:.1f}MB ({memory_before.percent:.1f}%)")
        
        # Force garbage collection
        collected = gc.collect()
        print(f"🧹 Garbage collection: {collected} objects collected")
        
        # Get memory after cleanup
        memory_after = psutil.virtual_memory()
        print(f"📊 Memory after cleanup: {memory_after.used / 1024 / 1024:.1f}MB ({memory_after.percent:.1f}%)")
        
        # Check if memory is too high
        if memory_after.percent > 90:
            print("⚠️  WARNING: Memory usage is very high!")
        elif memory_after.percent > 80:
            print("⚠️  WARNING: Memory usage is high")
        else:
            print("✅ Memory usage is normal")
            
    except ImportError:
        print("❌ psutil not available - cannot check memory")
    except Exception as e:
        print(f"❌ Error checking memory: {e}")

def test_signal_handling():
    """Test signal handling in background threads."""
    print("\n📡 Testing Signal Handling")
    print("=" * 50)
    
    try:
        import signal
        import threading
        
        def signal_handler(signum, frame):
            print(f"📡 Signal {signum} received")
        
        # Test in main thread
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            print("✅ Signal handler set in main thread")
        except Exception as e:
            print(f"❌ Error setting signal in main thread: {e}")
        
        # Test in background thread
        def test_background_signal():
            try:
                signal.signal(signal.SIGTERM, signal_handler)
                print("✅ Signal handler set in background thread")
            except ValueError as e:
                print(f"⚠️  Expected error in background thread: {e}")
            except Exception as e:
                print(f"❌ Unexpected error in background thread: {e}")
        
        thread = threading.Thread(target=test_background_signal)
        thread.start()
        thread.join()
        
    except Exception as e:
        print(f"❌ Error testing signal handling: {e}")

def main():
    """Run all tests."""
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    
    # Test memory usage first
    test_memory_usage()
    
    # Test signal handling
    test_signal_handling()
    
    # Test news generation
    test_news_generation()
    
    print(f"\n🕐 Test completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
