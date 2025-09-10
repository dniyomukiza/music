"""
Analytics routes for web-based dashboard
"""

from flask import Blueprint, render_template, jsonify, request
from .analytics import AppAnalytics
import json
import os

usage_analytics_bp = Blueprint('usage_analytics', __name__)

@usage_analytics_bp.route('/')
def usage_analytics_dashboard():
    """Main usage analytics dashboard page"""
    return render_template('analytics_dashboard.html')

@usage_analytics_bp.route('/api/usage-analytics/summary')
def analytics_summary():
    """Get summary analytics data"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        summary = analytics.get_summary_stats()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/daily')
def analytics_daily():
    """Get daily analytics data"""
    try:
        days = request.args.get('days', 7, type=int)
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        daily = analytics.get_daily_stats(days)
        return jsonify(daily)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/features')
def analytics_features():
    """Get feature usage analytics"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        features = analytics.get_feature_usage()
        return jsonify(features)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/devices')
def analytics_devices():
    """Get device/browser analytics"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        summary = analytics.get_summary_stats()
        return jsonify({
            'devices': summary['device_breakdown'],
            'browsers': summary['browser_breakdown'],
            'os': summary['os_breakdown']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/pages')
def analytics_pages():
    """Get page popularity analytics"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        summary = analytics.get_summary_stats()
        return jsonify({
            'top_pages': summary['top_pages'],
            'total_visits': summary['total_visits']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/peak-hours')
def analytics_peak_hours():
    """Get peak hours analytics"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        peak_hours = analytics.get_peak_hours()
        return jsonify(peak_hours)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@usage_analytics_bp.route('/api/usage-analytics/geographic')
def analytics_geographic():
    """Get geographic analytics"""
    try:
        analytics = AppAnalytics("visits.txt")
        if not analytics.visits:
            return jsonify({'error': 'No visits found'}), 404
        
        geo = analytics.get_geographic_insights()
        return jsonify(geo)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
