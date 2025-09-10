#!/usr/bin/env python3
"""
Quick analytics viewer for your music app
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analytics import AppAnalytics

def main():
    print("🎵 Music App Analytics Dashboard")
    print("=" * 50)
    
    # Check if visits.txt exists
    if not os.path.exists("visits.txt"):
        print("❌ visits.txt not found!")
        print("Make sure your app is running and generating logs.")
        return
    
    # Load analytics
    analytics = AppAnalytics("visits.txt")
    
    if not analytics.visits:
        print("❌ No visits found in the log file.")
        return
    
    # Generate and display report
    report = analytics.generate_report('text')
    print(report)
    
    # Additional insights
    print("\n" + "=" * 50)
    print("💡 QUICK INSIGHTS")
    print("=" * 50)
    
    summary = analytics.get_summary_stats()
    features = analytics.get_feature_usage()
    
    # Most used feature
    most_used_feature = max(features.items(), key=lambda x: x[1])
    print(f"🔥 Most Used Feature: {most_used_feature[0].replace('_', ' ').title()} ({most_used_feature[1]} times)")
    
    # Device preference
    device_breakdown = summary['device_breakdown']
    most_common_device = max(device_breakdown.items(), key=lambda x: x[1])
    print(f"📱 Most Common Device: {most_common_device[0]} ({most_common_device[1]} visits)")
    
    # Browser preference
    browser_breakdown = summary['browser_breakdown']
    most_common_browser = max(browser_breakdown.items(), key=lambda x: x[1])
    print(f"🌐 Most Common Browser: {most_common_browser[0]} ({most_common_browser[1]} visits)")
    
    # Recent activity
    daily = analytics.get_daily_stats(7)
    if daily:
        recent_days = list(daily.items())[-3:]
        print(f"📅 Recent Activity:")
        for date, stats in recent_days:
            print(f"   • {date}: {stats['total_visits']} visits, {stats['unique_visitors']} unique visitors")
    
    print(f"\n📊 Total Data Points: {len(analytics.visits)} visits analyzed")
    print("=" * 50)

if __name__ == "__main__":
    main()
