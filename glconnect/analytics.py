"""
Analytics module for tracking and viewing app usage statistics.
This module provides publicly accessible endpoints to view detailed analytics about page views and user behavior.
"""

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func, distinct
from datetime import datetime, timezone, timedelta
from .models import PageAnalytics, PageAnalyticsStats, db

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
def analytics_dashboard():
    """Main analytics dashboard page (public access)"""
    return render_template('analytics_dashboard.html')

@analytics_bp.route('/_analytics/api/stats')
def get_stats():
    """Get overall statistics"""
    try:
        # Total page views
        total_views = PageAnalytics.query.count()
        
        # Unique Flask endpoints (DB column legacy name: path)
        unique_endpoints = PageAnalytics.query.with_entities(
            func.count(distinct(PageAnalytics.endpoint))
        ).scalar()
        
        # Unique visitors (by IP)
        unique_visitors = PageAnalytics.query.with_entities(
            func.count(distinct(PageAnalytics.ip_address))
        ).scalar()
        
        # Authenticated vs anonymous views
        authenticated_views = PageAnalytics.query.filter_by(is_authenticated=True).count()
        anonymous_views = total_views - authenticated_views
        
        # Device stats
        device_stats = db.session.query(
            PageAnalytics.device,
            func.count(PageAnalytics.id).label('count')
        ).group_by(PageAnalytics.device).all()
        
        device_data = {device: count for device, count in device_stats if device}
        
        # Recent activity (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_views = PageAnalytics.query.filter(
            PageAnalytics.timestamp >= yesterday
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_views': total_views,
                'unique_endpoints': unique_endpoints,
                'unique_paths': unique_endpoints,
                'unique_visitors': unique_visitors,
                'authenticated_views': authenticated_views,
                'anonymous_views': anonymous_views,
                'device_stats': device_data,
                'recent_views_24h': recent_views
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/_analytics/api/pages')
def get_page_stats():
    """Get statistics by page/path"""
    try:
        # Filter by Flask endpoint (accept ?endpoint= or legacy ?path=)
        specific_endpoint = request.args.get('endpoint') or request.args.get('path')
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = db.session.query(
            PageAnalytics.endpoint,
            func.count(PageAnalytics.id).label('total_views'),
            func.count(distinct(PageAnalytics.ip_address)).label('unique_visitors'),
            func.max(PageAnalytics.timestamp).label('last_accessed')
        )
        
        if specific_endpoint:
            query = query.filter(PageAnalytics.endpoint == specific_endpoint)
        
        # Group by endpoint and order by total views
        results = query.group_by(PageAnalytics.endpoint).order_by(func.count(PageAnalytics.id).desc()).limit(limit).all()
        
        pages = []
        for endpoint, total_views, unique_visitors, last_accessed in results:
            pages.append({
                'endpoint': endpoint,
                'path': endpoint,
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'last_accessed': last_accessed.isoformat() if last_accessed else None
            })
        
        return jsonify({
            'success': True,
            'pages': pages
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/_analytics/api/recent-activity')
def get_recent_activity():
    """Get recent page view activity"""
    try:
        limit = int(request.args.get('limit', 50))
        
        # Get recent page views
        recent = PageAnalytics.query.order_by(
            PageAnalytics.timestamp.desc()
        ).limit(limit).all()
        
        activities = []
        for activity in recent:
            activities.append({
                'id': activity.id,
                'endpoint': activity.endpoint,
                'path': activity.endpoint,
                'ip_address': activity.ip_address,
                'device': activity.device,
                'is_authenticated': activity.is_authenticated,
                'user_id': activity.user_id,
                'timestamp': activity.timestamp.isoformat() if activity.timestamp else None,
            })
        
        return jsonify({
            'success': True,
            'activities': activities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/_analytics/api/time-series')
def get_time_series():
    """Get page views over time"""
    try:
        days = int(request.args.get('days', 7))
        group_by = request.args.get('group_by', 'hour')  # hour, day
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Base query
        query = PageAnalytics.query.filter(
            PageAnalytics.timestamp >= start_date
        )
        
        # Group by time period
        if group_by == 'hour':
            time_format = func.date_trunc('hour', PageAnalytics.timestamp)
        else:  # day
            time_format = func.date_trunc('day', PageAnalytics.timestamp)
        
        results = db.session.query(
            time_format.label('period'),
            func.count(PageAnalytics.id).label('count')
        ).filter(
            PageAnalytics.timestamp >= start_date
        ).group_by(
            time_format
        ).order_by(
            time_format
        ).all()
        
        time_series = []
        for period, count in results:
            time_series.append({
                'timestamp': period.isoformat() if period else None,
                'count': count
            })
        
        return jsonify({
            'success': True,
            'time_series': time_series
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/_analytics/api/top-paths')
def get_top_paths():
    """Get top visited paths"""
    try:
        limit = int(request.args.get('limit', 10))
        
        top_q = db.session.query(
            PageAnalytics.endpoint,
            func.count(PageAnalytics.id).label('views'),
            func.count(distinct(PageAnalytics.ip_address)).label('unique_visitors')
        ).group_by(
            PageAnalytics.endpoint
        ).order_by(
            func.count(PageAnalytics.id).desc()
        ).limit(limit).all()
        
        paths = []
        for endpoint, views, unique_visitors in top_q:
            paths.append({
                'endpoint': endpoint,
                'path': endpoint,
                'views': views,
                'unique_visitors': unique_visitors
            })
        
        return jsonify({
            'success': True,
            'top_paths': paths,
            'top_endpoints': paths
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

