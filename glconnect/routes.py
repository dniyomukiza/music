from flask import Blueprint, render_template, request, jsonify
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

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/health')
def health():
    """Health check endpoint for monitoring."""
    try:
        # Get memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Get system memory
        system_memory = psutil.virtual_memory()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'memory_usage_mb': round(memory_mb, 2),
            'system_memory_percent': round(system_memory.percent, 2),
            'system_memory_available_gb': round(system_memory.available / 1024 / 1024 / 1024, 2)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500
import glconnect.routes1
import glconnect.routes2

