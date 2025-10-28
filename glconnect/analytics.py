"""
Analytics module for tracking and viewing app usage statistics.
This module provides admin-only endpoints to view detailed analytics about page views and user behavior.
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func, distinct
from datetime import datetime, timezone, timedelta
from .models import PageAnalytics, PageAnalyticsStats, db

analytics_bp = Blueprint('analytics', __name__)

def admin_required(f):
    """Decorator to check if user is admin"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'}), 403
        return f(*args, **kwargs)
    return decorated_function

@analytics_bp.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    """Main analytics dashboard page (admin only)"""
    return render_template('analytics_dashboard.html')

@analytics_bp.route('/_analytics/api/stats')
@login_required
@admin_required
def get_stats():
    """Get overall statistics"""
    try:
        # Total page views
        total_views = PageAnalytics.query.count()
        
        # Unique paths
        unique_paths = PageAnalytics.query.with_entities(
            func.count(distinct(PageAnalytics.path))
        ).scalar()
        
        # Unique visitors (by IP)
        unique_visitors = PageAnalytics.query.with_entities(
            func.count(distinct(PageAnalytics.ip_address))
        ).scalar()
        
        # Authenticated vs anonymous views
        authenticated_views = PageAnalytics.query.filter_by(is_authenticated=True).count()
        anonymous_views = total_views - authenticated_views
        
        # Browser stats
        browser_stats = db.session.query(
            PageAnalytics.browser,
            func.count(PageAnalytics.id).label('count')
        ).group_by(PageAnalytics.browser).all()
        
        browser_data = {browser: count for browser, count in browser_stats if browser}
        
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
                'unique_paths': unique_paths,
                'unique_visitors': unique_visitors,
                'authenticated_views': authenticated_views,
                'anonymous_views': anonymous_views,
                'browser_stats': browser_data,
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
@login_required
@admin_required
def get_page_stats():
    """Get statistics by page/path"""
    try:
        # Get path parameter for filtering specific page
        specific_path = request.args.get('path')
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = db.session.query(
            PageAnalytics.path,
            func.count(PageAnalytics.id).label('total_views'),
            func.count(distinct(PageAnalytics.ip_address)).label('unique_visitors'),
            func.max(PageAnalytics.timestamp).label('last_accessed')
        )
        
        if specific_path:
            query = query.filter(PageAnalytics.path == specific_path)
        
        # Group by path and order by total views
        results = query.group_by(PageAnalytics.path).order_by(func.count(PageAnalytics.id).desc()).limit(limit).all()
        
        pages = []
        for path, total_views, unique_visitors, last_accessed in results:
            pages.append({
                'path': path,
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
@login_required
@admin_required
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
                'path': activity.path,
                'method': activity.method,
                'ip_address': activity.ip_address,
                'browser': activity.browser,
                'device': activity.device,
                'is_authenticated': activity.is_authenticated,
                'user_id': activity.user_id,
                'timestamp': activity.timestamp.isoformat() if activity.timestamp else None,
                'referer': activity.referer
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
@login_required
@admin_required
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
@login_required
@admin_required
def get_top_paths():
    """Get top visited paths"""
    try:
        limit = int(request.args.get('limit', 10))
        
        top_paths = db.session.query(
            PageAnalytics.path,
            func.count(PageAnalytics.id).label('views'),
            func.count(distinct(PageAnalytics.ip_address)).label('unique_visitors')
        ).group_by(
            PageAnalytics.path
        ).order_by(
            func.count(PageAnalytics.id).desc()
        ).limit(limit).all()
        
        paths = []
        for path, views, unique_visitors in top_paths:
            paths.append({
                'path': path,
                'views': views,
                'unique_visitors': unique_visitors
            })
        
        return jsonify({
            'success': True,
            'top_paths': paths
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

