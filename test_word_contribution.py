#!/usr/bin/env python3
"""
Test script for word contribution functionality
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_contribution_submission():
    """Test submitting a word contribution"""
    print("🧪 Testing Word Contribution Submission")
    print("=" * 50)
    
    # Test data
    test_contributions = [
        {
            "word": "umugabo",
            "meaning": "A man or male person",
            "example_sentence": "Umugabo yaje mu nzu.",
            "part_of_speech": "noun",
            "phonetics": "/u-mu-ga-bo/",
            "contributor_name": "Test User"
        },
        {
            "word": "gukora",
            "meaning": "To work or do something",
            "example_sentence": "Ndi gukora mu biro.",
            "part_of_speech": "verb",
            "phonetics": "/gu-ko-ra/",
            "contributor_name": "Test User 2"
        }
    ]
    
    base_url = "http://localhost:5000"
    
    for i, contribution in enumerate(test_contributions, 1):
        print(f"\n📝 Test {i}: Submitting word '{contribution['word']}'")
        
        try:
            response = requests.post(
                f"{base_url}/routes1/contribute-word",
                data=contribution,
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success: {data.get('message', 'No message')}")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Error: Could not connect to server. Make sure the Flask app is running.")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    return True

def test_duplicate_submission():
    """Test submitting a duplicate word"""
    print("\n🔄 Testing Duplicate Word Submission")
    print("=" * 50)
    
    # Try to submit the same word twice
    contribution = {
        "word": "umugabo",  # Same word as first test
        "meaning": "Another definition for man",
        "contributor_name": "Test User 3"
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/routes1/contribute-word",
            data=contribution,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 400:
            data = response.json()
            print(f"   ✅ Correctly rejected: {data.get('message', 'No message')}")
            return True
        else:
            print(f"   ❌ Should have been rejected: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_missing_fields():
    """Test submitting with missing required fields"""
    print("\n❌ Testing Missing Required Fields")
    print("=" * 50)
    
    # Submit without required fields
    contribution = {
        "word": "",  # Empty word
        "meaning": "Some meaning"
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/routes1/contribute-word",
            data=contribution,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 400:
            data = response.json()
            print(f"   ✅ Correctly rejected: {data.get('message', 'No message')}")
            return True
        else:
            print(f"   ❌ Should have been rejected: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_vocabulary_page():
    """Test that the vocabulary page loads with contribution form"""
    print("\n🌐 Testing Vocabulary Page")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:5000/routes1/words", timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if "Contribute a New Word" in content and "contributionForm" in content:
                print("   ✅ Vocabulary page loads with contribution form")
                return True
            else:
                print("   ❌ Contribution form not found on page")
                return False
        else:
            print(f"   ❌ Error loading page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Word Contribution Functionality Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Vocabulary Page Load", test_vocabulary_page),
        ("Word Contribution Submission", test_contribution_submission),
        ("Duplicate Word Rejection", test_duplicate_submission),
        ("Missing Fields Validation", test_missing_fields),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"   ✅ PASSED")
            else:
                print(f"   ❌ FAILED")
        except Exception as e:
            print(f"   ❌ FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Word contribution functionality is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

