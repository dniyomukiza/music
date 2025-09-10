#!/usr/bin/env python3
"""
Enhanced logging system for better analytics
"""

import json
import os
from datetime import datetime, timezone
from flask import request, g
import re

class EnhancedLogger:
    def __init__(self, log_file="visits.txt", detailed_log="detailed_visits.json"):
        self.log_file = log_file
        self.detailed_log = detailed_log
        self.ensure_log_files()
    
    def ensure_log_files(self):
        """Ensure log files exist and are writable"""
        for file_path in [self.log_file, self.detailed_log]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write("")
    
    def log_visit(self, request, response=None):
        """Log a visit with enhanced details"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Basic log (backward compatible)
            basic_log = f"{timestamp} | {request.remote_addr} | {request.method} {request.path} | {request.headers.get('User-Agent', 'Unknown')}\n"
            
            with open(self.log_file, "a") as f:
                f.write(basic_log)
            
            # Enhanced detailed log
            detailed_entry = {
                'timestamp': timestamp,
                'ip': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'full_path': request.full_path,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'referrer': request.headers.get('Referer', ''),
                'accept_language': request.headers.get('Accept-Language', ''),
                'accept_encoding': request.headers.get('Accept-Encoding', ''),
                'connection': request.headers.get('Connection', ''),
                'host': request.headers.get('Host', ''),
                'x_forwarded_for': request.headers.get('X-Forwarded-For', ''),
                'x_real_ip': request.headers.get('X-Real-IP', ''),
                'query_params': dict(request.args),
                'form_data': dict(request.form) if request.form else {},
                'response_status': response.status_code if response else None,
                'response_size': response.content_length if response else None,
                'session_id': getattr(g, 'session_id', None),
                'user_id': getattr(g, 'user_id', None),
                'processing_time': getattr(g, 'processing_time', None)
            }
            
            # Add device/browser info
            device_info = self.parse_user_agent(request.headers.get('User-Agent', ''))
            detailed_entry.update(device_info)
            
            # Add feature detection
            feature_info = self.detect_features(request.path, request.method, request.args)
            detailed_entry.update(feature_info)
            
            # Write detailed log
            with open(self.detailed_log, "a") as f:
                f.write(json.dumps(detailed_entry) + "\n")
                
        except Exception as e:
            print(f"Error logging visit: {e}")
    
    def parse_user_agent(self, user_agent):
        """Parse user agent for device/browser info"""
        device = "Unknown"
        browser = "Unknown"
        os = "Unknown"
        is_mobile = False
        is_bot = False
        
        ua_lower = user_agent.lower()
        
        # Bot detection
        bot_keywords = ['bot', 'crawler', 'spider', 'scraper', 'norton', 'security']
        if any(keyword in ua_lower for keyword in bot_keywords):
            is_bot = True
            device = "Bot"
        
        # Device detection
        if not is_bot:
            if any(x in ua_lower for x in ['mobile', 'android', 'iphone']):
                device = "Mobile"
                is_mobile = True
            elif any(x in ua_lower for x in ['tablet', 'ipad']):
                device = "Tablet"
                is_mobile = True
            elif any(x in ua_lower for x in ['macintosh', 'windows', 'linux']):
                device = "Desktop"
        
        # Browser detection
        if not is_bot:
            if 'chrome' in ua_lower and 'edge' not in ua_lower:
                browser = "Chrome"
            elif 'firefox' in ua_lower:
                browser = "Firefox"
            elif 'safari' in ua_lower and 'chrome' not in ua_lower:
                browser = "Safari"
            elif 'edge' in ua_lower:
                browser = "Edge"
            elif 'opera' in ua_lower:
                browser = "Opera"
        
        # OS detection
        if not is_bot:
            if 'macintosh' in ua_lower:
                os = "macOS"
            elif 'windows' in ua_lower:
                os = "Windows"
            elif 'linux' in ua_lower:
                os = "Linux"
            elif 'android' in ua_lower:
                os = "Android"
            elif 'iphone' in ua_lower or 'ipad' in ua_lower:
                os = "iOS"
        
        return {
            'device_type': device,
            'browser': browser,
            'operating_system': os,
            'is_mobile': is_mobile,
            'is_bot': is_bot
        }
    
    def detect_features(self, path, method, args):
        """Detect which features are being used"""
        path_lower = path.lower()
        
        features = {
            'feature_word_search': False,
            'feature_word_games': False,
            'feature_community_dictionary': False,
            'feature_contribute_words': False,
            'feature_music': False,
            'feature_blog': False,
            'feature_api': False,
            'feature_static': False
        }
        
        # Feature detection
        if 'words' in path_lower or 'search' in path_lower:
            features['feature_word_search'] = True
        elif 'game' in path_lower or 'matching' in path_lower:
            features['feature_word_games'] = True
        elif 'community' in path_lower:
            features['feature_community_dictionary'] = True
        elif 'contribute' in path_lower:
            features['feature_contribute_words'] = True
        elif any(x in path_lower for x in ['music', 'artist', 'playlist', 'song']):
            features['feature_music'] = True
        elif any(x in path_lower for x in ['blog', 'news', 'article']):
            features['feature_blog'] = True
        elif path_lower.startswith('/api/'):
            features['feature_api'] = True
        elif any(x in path_lower for x in ['static', 'css', 'js', 'images', 'audio']):
            features['feature_static'] = True
        
        return features

# Flask integration
def init_enhanced_logging(app):
    """Initialize enhanced logging for Flask app"""
    logger = EnhancedLogger()
    
    @app.before_request
    def before_request():
        g.start_time = datetime.now()
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            g.processing_time = (datetime.now() - g.start_time).total_seconds()
        
        logger.log_visit(request, response)
        return response
    
    return logger
