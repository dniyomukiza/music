#!/usr/bin/env python3
"""
Test script for topic validation system
Tests various inputs including irrelevant ones to see system response
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect.news_routes import is_relevant_topic, get_validation_suggestions, get_topic_validation_info

def test_validation():
    """Test the validation system with various inputs"""
    
    test_cases = [
        # Valid news topics
        ("Ebola outbreak in Congo", "Valid news topic"),
        ("Ukraine war updates", "Valid news topic"),
        ("Stock market crash", "Valid news topic"),
        ("Breaking: Election results", "Valid news topic"),
        ("COVID-19 pandemic", "Valid news topic"),
        ("Climate change summit", "Valid news topic"),
        ("Protest in France", "Valid news topic"),
        ("NASA space mission", "Valid news topic"),
        ("Economic recession", "Valid news topic"),
        ("Corruption scandal", "Valid news topic"),
        
        # Personal/irrelevant statements
        ("I am going to school", "Personal statement"),
        ("My cat is cute", "Personal statement"),
        ("How are you?", "Casual conversation"),
        ("I like pizza", "Personal opinion"),
        ("Today I went to work", "Personal activity"),
        ("My car broke down", "Personal problem"),
        ("I think it's nice", "Personal opinion"),
        ("What's up?", "Casual conversation"),
        ("Thanks for helping", "Casual conversation"),
        ("I need help", "Personal request"),
        
        # Edge cases
        ("Purple elephant dancing", "Unusual but not personal"),
        ("Random gibberish xyz", "Nonsense"),
        ("123", "Numbers only"),
        ("a", "Too short"),
        ("", "Empty"),
        ("hello", "Casual greeting"),
        ("test", "Testing word"),
        
        # Single words
        ("war", "Single news word"),
        ("politics", "Single news word"),
        ("economy", "Single news word"),
        ("technology", "Single news word"),
        ("health", "Single news word"),
        ("international", "Single news word"),
        ("trade", "Single news word"),
        
        # Mixed cases
        ("I am going to war", "Personal + news word"),
        ("My country's economy", "Personal + news word"),
        ("Today's election results", "Time + news"),
        ("Breaking news about my cat", "News format + personal"),
    ]
    
    print("=" * 80)
    print("TOPIC VALIDATION TEST RESULTS")
    print("=" * 80)
    
    for topic, description in test_cases:
        print(f"\n📝 Testing: '{topic}'")
        print(f"   Description: {description}")
        print("-" * 60)
        
        try:
            # Test basic validation
            is_relevant, confidence, reason = is_relevant_topic(topic)
            print(f"   ✅ Result: {'ACCEPTED' if is_relevant else 'REJECTED'}")
            print(f"   📊 Confidence: {confidence:.2f}")
            print(f"   💭 Reason: {reason}")
            
            # Test suggestions if rejected
            if not is_relevant:
                suggestions = get_validation_suggestions(topic)
                if suggestions:
                    print(f"   💡 Suggestions:")
                    for suggestion in suggestions:
                        print(f"      • {suggestion}")
            
            # Test comprehensive info
            validation_info = get_topic_validation_info(topic)
            print(f"   🔍 Can Override: {'Yes' if validation_info['can_override'] else 'No'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Count results
    accepted = 0
    rejected = 0
    errors = 0
    
    for topic, description in test_cases:
        try:
            is_relevant, confidence, reason = is_relevant_topic(topic)
            if is_relevant:
                accepted += 1
            else:
                rejected += 1
        except:
            errors += 1
    
    print(f"Total tests: {len(test_cases)}")
    print(f"Accepted: {accepted}")
    print(f"Rejected: {rejected}")
    print(f"Errors: {errors}")
    print(f"Success rate: {((accepted + rejected) / len(test_cases)) * 100:.1f}%")

if __name__ == "__main__":
    test_validation()
