from flask import Blueprint, render_template

bp = Blueprint('routes', __name__)
@bp.route('/')
def index():
    """Render the home page."""
    return render_template('home.html')
import glconnect.routes1
import glconnect.routes2

