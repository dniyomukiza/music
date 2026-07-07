"""
Analytics module for tracking and viewing app usage statistics.
"""

import os
from collections import defaultdict

from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from sqlalchemy import func, distinct
from datetime import date, datetime, time, timezone, timedelta
from .models import PageAnalytics, db

analytics_bp = Blueprint('analytics', __name__)

ANALYTICS_SITE_HOST = (
    os.getenv("FRONTEND_BASE_URL", "https://ndotonic.com")
    .replace("https://", "")
    .replace("http://", "")
    .rstrip("/")
    .removeprefix("www.")
)


def normalize_request_path(path):
    """Canonical path key for analytics grouping."""
    if not path or path == "/":
        return "/"
    return path.rstrip("/") or "/"


def _rule_to_display_path(rule):
    """Turn a Flask URL rule into a readable ndotonic.com path."""
    path = rule
    for token in ("<int:", "<float:", "<path:", "<uuid:", "<string:", "<"):
        if token in path:
            idx = path.index("<")
            end = path.index(">", idx) + 1
            path = path[:idx] + "*" + path[end:]
    path = path.replace("//", "/")
    return normalize_request_path(path)


def resolve_analytics_path(stored_value):
    """Resolve stored request path or legacy Flask endpoint to a URL path."""
    if not stored_value:
        return "/"
    if stored_value.startswith("/"):
        return normalize_request_path(stored_value)

    try:
        return normalize_request_path(url_for(stored_value))
    except Exception:
        pass

    try:
        rules = [
            rule
            for rule in current_app.url_map.iter_rules(stored_value)
            if "GET" in rule.methods and rule.rule != "/static/<path:filename>"
        ]
        if rules:
            rules.sort(key=lambda r: (("<" in r.rule), len(r.rule)))
            return _rule_to_display_path(rules[0].rule)
    except Exception:
        pass

    return stored_value


def format_site_path(stored_value):
    """Human-readable ndotonic.com path for the dashboard."""
    resolved = resolve_analytics_path(stored_value)
    if not resolved or resolved == "/":
        return ANALYTICS_SITE_HOST
    if resolved.startswith("/"):
        return f"{ANALYTICS_SITE_HOST}{resolved}"
    return f"{ANALYTICS_SITE_HOST}/{resolved}"


def _day_bucket(column):
    """Group timestamps by calendar day (PostgreSQL + SQLite)."""
    if db.engine.dialect.name == "postgresql":
        return func.date_trunc("day", column)
    return func.date(column)


def _timestamp_to_day_label(day):
    if day is None:
        return None
    if isinstance(day, str):
        return day[:10]
    if hasattr(day, "date"):
        return day.date().isoformat()
    return day.isoformat()[:10]


def _day_bounds_utc(day_label):
    """UTC [start, end) for a calendar day YYYY-MM-DD."""
    day = date.fromisoformat(day_label)
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


@analytics_bp.route('/analytics')
def analytics_dashboard():
    """Main analytics dashboard page (public access)."""
    return render_template('analytics_dashboard.html')


@analytics_bp.route('/_analytics/api/dashboard')
def get_dashboard():
    """Daily view counts per page."""
    try:
        filter_date = (request.args.get("date") or "").strip()
        day_expr = _day_bucket(PageAnalytics.timestamp)
        query = db.session.query(
            day_expr.label("day"),
            PageAnalytics.endpoint,
            func.count(PageAnalytics.id).label("views"),
        )

        if filter_date:
            try:
                date.fromisoformat(filter_date)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date. Use YYYY-MM-DD."}), 400
            start, end = _day_bounds_utc(filter_date)
            query = query.filter(
                PageAnalytics.timestamp >= start,
                PageAnalytics.timestamp < end,
            )
            days = 1
        else:
            days = min(max(int(request.args.get("days", 30)), 1), 365)
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(PageAnalytics.timestamp >= start_date)

        daily_rows = query.group_by(day_expr, PageAnalytics.endpoint).all()

        merged_daily = defaultdict(int)
        for day, stored, views in daily_rows:
            day_label = _timestamp_to_day_label(day)
            if not day_label:
                continue
            display_path = format_site_path(stored)
            merged_daily[(day_label, display_path)] += views

        daily_views = [
            {"date": day_label, "path": path, "views": count}
            for (day_label, path), count in merged_daily.items()
        ]
        daily_views.sort(key=lambda row: (row["date"], row["views"], row["path"]), reverse=True)

        total_views = sum(row["views"] for row in daily_views)

        return jsonify({
            "success": True,
            "days": days,
            "filter_date": filter_date or None,
            "total_views": total_views,
            "daily_views": daily_views,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
            if db.engine.dialect.name == "postgresql":
                time_format = func.date_trunc('hour', PageAnalytics.timestamp)
            else:
                time_format = func.strftime('%Y-%m-%d %H:00:00', PageAnalytics.timestamp)
        else:
            time_format = _day_bucket(PageAnalytics.timestamp)
        
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

