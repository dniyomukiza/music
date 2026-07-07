"""
Analytics module for tracking and viewing app usage statistics.
"""

import os
from collections import defaultdict

from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from sqlalchemy import func, distinct
from datetime import datetime, timezone, timedelta
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


@analytics_bp.route('/analytics')
def analytics_dashboard():
    """Main analytics dashboard page (public access)."""
    return render_template('analytics_dashboard.html')


@analytics_bp.route('/_analytics/api/dashboard')
def get_dashboard():
    """Daily view counts and endpoint visit totals."""
    try:
        days = min(max(int(request.args.get('days', 30)), 1), 365)
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        day_expr = _day_bucket(PageAnalytics.timestamp)
        daily_rows = (
            db.session.query(
                day_expr.label("day"),
                func.count(PageAnalytics.id).label("views"),
            )
            .filter(PageAnalytics.timestamp >= start_date)
            .group_by(day_expr)
            .order_by(day_expr)
            .all()
        )

        daily_views = []
        for day, views in daily_rows:
            if day is None:
                continue
            if isinstance(day, str):
                day_label = day[:10]
            else:
                day_label = day.date().isoformat() if hasattr(day, "date") else day.isoformat()[:10]
            daily_views.append({"date": day_label, "views": views})

        endpoint_rows = (
            db.session.query(
                PageAnalytics.endpoint,
                func.count(PageAnalytics.id).label("views"),
                func.max(PageAnalytics.timestamp).label("last_visited"),
            )
            .filter(PageAnalytics.timestamp >= start_date)
            .group_by(PageAnalytics.endpoint)
            .all()
        )

        merged_pages = defaultdict(lambda: {"views": 0, "last_visited": None, "raw_keys": set()})
        for stored, views, last_visited in endpoint_rows:
            display_path = format_site_path(stored)
            bucket = merged_pages[display_path]
            bucket["views"] += views
            bucket["raw_keys"].add(stored)
            if last_visited and (
                bucket["last_visited"] is None or last_visited > bucket["last_visited"]
            ):
                bucket["last_visited"] = last_visited

        pages = []
        for display_path, data in merged_pages.items():
            pages.append({
                "path": display_path,
                "views": data["views"],
                "last_visited": data["last_visited"].isoformat() if data["last_visited"] else None,
            })
        pages.sort(key=lambda row: (-row["views"], row["path"]))

        total_views = sum(row["views"] for row in daily_views)

        return jsonify({
            "success": True,
            "days": days,
            "total_views": total_views,
            "daily_views": daily_views,
            "pages": pages,
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

