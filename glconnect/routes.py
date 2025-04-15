from flask import Blueprint, render_template

bp = Blueprint('routes', __name__)
@bp.route('/')
def index():
    """Render the home page."""
    return render_template('landing.html')
@bp.route('/landing')
def landing():
    return render_template('home.html')
@bp.route('/about')
def about():
    return render_template('about.html')
import glconnect.routes1
import glconnect.routes2

