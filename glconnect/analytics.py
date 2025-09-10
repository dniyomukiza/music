#!/usr/bin/env python3
"""
Enhanced Analytics for Music App Usage
Analyzes visits.txt to provide detailed insights
"""

import re
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
import argparse

class AppAnalytics:
    def __init__(self, visits_file="visits.txt"):
        self.visits_file = visits_file
        self.visits = []
        self.load_visits()
    
    def load_visits(self):
        """Load and parse visits from the log file"""
        if not Path(self.visits_file).exists():
            print(f"❌ {self.visits_file} not found!")
            return
        
        with open(self.visits_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse: timestamp | IP | method path | user_agent
                    parts = line.split(' | ', 3)
                    if len(parts) >= 4:
                        timestamp_str, ip, method_path, user_agent = parts
                        
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        # Parse method and path
                        method, path = method_path.split(' ', 1)
                        
                        # Extract device info from user agent
                        device_info = self.parse_user_agent(user_agent)
                        
                        self.visits.append({
                            'timestamp': timestamp,
                            'ip': ip,
                            'method': method,
                            'path': path,
                            'user_agent': user_agent,
                            'device': device_info['device'],
                            'browser': device_info['browser'],
                            'os': device_info['os']
                        })
                except Exception as e:
                    print(f"⚠️  Error parsing line: {line[:50]}... - {e}")
    
    def parse_user_agent(self, user_agent):
        """Extract device, browser, and OS info from user agent"""
        device = "Unknown"
        browser = "Unknown"
        os = "Unknown"
        
        # Device detection
        if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            device = "Mobile"
        elif "Tablet" in user_agent or "iPad" in user_agent:
            device = "Tablet"
        elif "Macintosh" in user_agent or "Windows" in user_agent or "Linux" in user_agent:
            device = "Desktop"
        
        # Browser detection
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
        elif "Norton" in user_agent:
            browser = "Norton"
        
        # OS detection
        if "Macintosh" in user_agent:
            os = "macOS"
        elif "Windows" in user_agent:
            os = "Windows"
        elif "Linux" in user_agent:
            os = "Linux"
        elif "Android" in user_agent:
            os = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            os = "iOS"
        
        return {'device': device, 'browser': browser, 'os': os}
    
    def get_summary_stats(self):
        """Get overall summary statistics"""
        if not self.visits:
            return {"error": "No visits found"}
        
        total_visits = len(self.visits)
        unique_ips = len(set(v['ip'] for v in self.visits))
        
        # Time range
        timestamps = [v['timestamp'] for v in self.visits]
        first_visit = min(timestamps)
        last_visit = max(timestamps)
        duration = last_visit - first_visit
        
        # Most popular pages
        page_counts = Counter(v['path'] for v in self.visits)
        top_pages = page_counts.most_common(10)
        
        # Device breakdown
        device_counts = Counter(v['device'] for v in self.visits)
        browser_counts = Counter(v['browser'] for v in self.visits)
        os_counts = Counter(v['os'] for v in self.visits)
        
        return {
            'total_visits': total_visits,
            'unique_visitors': unique_ips,
            'first_visit': first_visit.isoformat(),
            'last_visit': last_visit.isoformat(),
            'duration_days': duration.days,
            'top_pages': top_pages,
            'device_breakdown': dict(device_counts),
            'browser_breakdown': dict(browser_counts),
            'os_breakdown': dict(os_counts)
        }
    
    def get_daily_stats(self, days=7):
        """Get daily visit statistics for the last N days"""
        if not self.visits:
            return {}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_visits = defaultdict(int)
        daily_unique = defaultdict(set)
        
        for visit in self.visits:
            if visit['timestamp'].date() >= start_date.date():
                date_key = visit['timestamp'].date().isoformat()
                daily_visits[date_key] += 1
                daily_unique[date_key].add(visit['ip'])
        
        return {
            date: {
                'total_visits': count,
                'unique_visitors': len(daily_unique[date])
            }
            for date, count in sorted(daily_visits.items())
        }
    
    def get_feature_usage(self):
        """Analyze usage of specific features"""
        feature_usage = {
            'word_search': 0,
            'word_games': 0,
            'community_dictionary': 0,
            'contribute_words': 0,
            'music_features': 0,
            'blog_features': 0
        }
        
        for visit in self.visits:
            path = visit['path'].lower()
            
            if 'words' in path or 'search' in path:
                feature_usage['word_search'] += 1
            elif 'game' in path or 'matching' in path:
                feature_usage['word_games'] += 1
            elif 'community' in path:
                feature_usage['community_dictionary'] += 1
            elif 'contribute' in path:
                feature_usage['contribute_words'] += 1
            elif 'music' in path or 'artist' in path or 'playlist' in path:
                feature_usage['music_features'] += 1
            elif 'blog' in path or 'news' in path:
                feature_usage['blog_features'] += 1
        
        return feature_usage
    
    def get_peak_hours(self):
        """Get peak usage hours"""
        hour_counts = Counter(v['timestamp'].hour for v in self.visits)
        return dict(hour_counts.most_common(24))
    
    def get_geographic_insights(self):
        """Analyze IP patterns for geographic insights"""
        ip_counts = Counter(v['ip'] for v in self.visits)
        
        # Categorize IPs
        local_ips = [ip for ip in ip_counts.keys() if ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.')]
        external_ips = [ip for ip in ip_counts.keys() if ip not in local_ips]
        
        return {
            'local_visits': sum(ip_counts[ip] for ip in local_ips),
            'external_visits': sum(ip_counts[ip] for ip in external_ips),
            'unique_local_ips': len(local_ips),
            'unique_external_ips': len(external_ips),
            'top_ips': dict(ip_counts.most_common(10))
        }
    
    def generate_report(self, format='text'):
        """Generate a comprehensive analytics report"""
        if not self.visits:
            return "❌ No visits found in the log file."
        
        summary = self.get_summary_stats()
        daily = self.get_daily_stats()
        features = self.get_feature_usage()
        peak_hours = self.get_peak_hours()
        geo = self.get_geographic_insights()
        
        if format == 'json':
            return json.dumps({
                'summary': summary,
                'daily_stats': daily,
                'feature_usage': features,
                'peak_hours': peak_hours,
                'geographic': geo
            }, indent=2)
        
        # Text format
        report = f"""
🎵 MUSIC APP ANALYTICS REPORT
{'='*50}

📊 OVERVIEW
• Total Visits: {summary['total_visits']:,}
• Unique Visitors: {summary['unique_visitors']:,}
• First Visit: {summary['first_visit']}
• Last Visit: {summary['last_visit']}
• Duration: {summary['duration_days']} days

📱 DEVICE BREAKDOWN
"""
        for device, count in summary['device_breakdown'].items():
            percentage = (count / summary['total_visits']) * 100
            report += f"• {device}: {count} ({percentage:.1f}%)\n"
        
        report += f"\n🌐 BROWSER BREAKDOWN\n"
        for browser, count in summary['browser_breakdown'].items():
            percentage = (count / summary['total_visits']) * 100
            report += f"• {browser}: {count} ({percentage:.1f}%)\n"
        
        report += f"\n💻 OPERATING SYSTEM\n"
        for os, count in summary['os_breakdown'].items():
            percentage = (count / summary['total_visits']) * 100
            report += f"• {os}: {count} ({percentage:.1f}%)\n"
        
        report += f"\n🔥 TOP PAGES\n"
        for page, count in summary['top_pages'][:5]:
            percentage = (count / summary['total_visits']) * 100
            report += f"• {page}: {count} visits ({percentage:.1f}%)\n"
        
        report += f"\n🎯 FEATURE USAGE\n"
        for feature, count in features.items():
            percentage = (count / summary['total_visits']) * 100
            report += f"• {feature.replace('_', ' ').title()}: {count} ({percentage:.1f}%)\n"
        
        report += f"\n⏰ PEAK HOURS (Top 5)\n"
        for hour, count in list(peak_hours.items())[:5]:
            report += f"• {hour:02d}:00 - {count} visits\n"
        
        report += f"\n🌍 GEOGRAPHIC INSIGHTS\n"
        report += f"• Local Visits: {geo['local_visits']} ({geo['local_visits']/summary['total_visits']*100:.1f}%)\n"
        report += f"• External Visits: {geo['external_visits']} ({geo['external_visits']/summary['total_visits']*100:.1f}%)\n"
        
        if daily:
            report += f"\n📅 RECENT ACTIVITY (Last 7 Days)\n"
            for date, stats in list(daily.items())[-7:]:
                report += f"• {date}: {stats['total_visits']} visits, {stats['unique_visitors']} unique\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Analyze app usage from visits.txt')
    parser.add_argument('--file', default='visits.txt', help='Path to visits.txt file')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--days', type=int, default=7, help='Days for daily stats')
    
    args = parser.parse_args()
    
    analytics = AppAnalytics(args.file)
    report = analytics.generate_report(args.format)
    print(report)

if __name__ == "__main__":
    main()
