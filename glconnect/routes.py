from flask import Blueprint, render_template,request
from datetime import datetime, timezone


bp = Blueprint('routes', __name__)
@bp.before_request
def log_request():
    try:
        with open("visits.txt", "a") as f:
            timestamp = datetime.now(timezone.utc).isoformat()
            f.write(f"{timestamp} | {request.remote_addr} | {request.method} {request.path} | {request.headers.get('User-Agent')}\n")
    except Exception as ex:
        print("Exception occured while logging: ",ex)
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
import glconnect.routes1
import glconnect.routes2

