from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
import psutil
import os


bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    """Render the home page."""
    return render_template('landing.html')

@bp.route('/home')
def home():
    return render_template('home.html')

@bp.route('/marketplace')
@login_required
def marketplace():
    """Universal marketplace access - redirects to Ink Studio marketplace"""
    return redirect(url_for('book_platform.marketplace'))

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/careers')
def careers():
    """Careers page with job openings."""
    return render_template('careers.html')

@bp.route('/health')
def health():
    """Health check endpoint for monitoring and Docker healthchecks.

    Always returns HTTP 200 if the app process is serving requests. Metrics are best-effort:
    psutil can fail in some container/cgroup setups; a 500 here breaks Docker's urllib
    healthcheck and nginx depends_on: service_healthy.
    """
    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        system_memory = psutil.virtual_memory()
        payload.update({
            'status': 'healthy',
            'memory_usage_mb': round(memory_mb, 2),
            'system_memory_percent': round(system_memory.percent, 2),
            'system_memory_available_gb': round(system_memory.available / 1024 / 1024 / 1024, 2),
        })
    except Exception as e:
        payload.update({
            'status': 'degraded',
            'error': str(e),
        })
    return jsonify(payload), 200
import glconnect.routes1
import glconnect.routes2

