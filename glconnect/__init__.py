import os
import json
import re
from datetime import datetime, timezone
from flask import Flask, request
from .models import db, User
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect
from flask_login import LoginManager
from flask_mail import Mail
from flask_ckeditor import CKEditor
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration from environment variables (more reliable than file mounting)
config = {
    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    "OPENAI_AI_KEY": os.getenv("OPENAI_AI_KEY"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json"),
    "DB_URL": os.getenv("DB_URL"),
    "RECAPTCHAPUB": os.getenv("RECAPTCHAPUB"),
    "RECAPTCHAPRIV": os.getenv("RECAPTCHAPRIV")
}
print("DEBUG: Using environment variables for configuration")

# Debug: Check if Google credentials are loaded
# Get Google API key from glconfig.json
google_api_key = config.get("GOOGLE_API_KEY")
gemini_api_key = config.get("GEMINI_API_KEY")
print(f"GOOGLE_API_KEY from glconfig.json: {google_api_key}")
print(f"GEMINI_API_KEY from .env: {gemini_api_key[:20]}..." if gemini_api_key else "GEMINI_API_KEY: Not found")
print(f"GOOGLE_APPLICATION_CREDENTIALS: tts.json (local file)")

# Initialize extensions
mail = Mail()
jwt = JWTManager()
login_manager = LoginManager()

# Use the same config loaded above

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    CORS(app, origins=["https://glc.cool"], supports_credentials=True) # <-- ADD supports_credentials=True

    # Secure session cookie configuration
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None', # This is correct for cross-site cookies with credentials
        JWT_SECRET_KEY="abarayon",
        GEMINI_API_KEY=config.get("GEMINI_API_KEY"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,  # 2 GB max upload size
    )

    # Secret key for sessions
    app.secret_key = os.urandom(24)

    # Add hasattr to Jinja2 globals for use in templates
    app.jinja_env.globals['hasattr'] = hasattr

    # CKEditor configuration
    ckeditor = CKEditor() 
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['CKEDITOR_PKG_TYPE'] = 'full'

    # Mail and recaptcha configuration
    app.config['RECAPTCHA_PUBLIC_KEY'] = config.get('RECAPTCHAPUB')
    app.config['RECAPTCHA_PRIVATE_KEY'] = config.get('RECAPTCHAPRIV')

    # Database and JWT configuration
    db_url = config.get('DB_URL')
    if db_url and 'postgresql://' in db_url:
        # Add SSL configuration for PostgreSQL
        if '?' in db_url:
            db_url += '&sslmode=require'
        else:
            db_url += '?sslmode=require'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_reset_on_return': 'commit',  # Reset connections on return
    }
    app.config["JWT_SECRET_KEY"] = "abarayon"

    # Initialize extensions
    db.init_app(app)
    
    # Add teardown handler to rollback failed transactions
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Rollback database session on errors to prevent 'transaction aborted' errors"""
        try:
            # Always rollback on exception to clear any failed transactions
            if exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass  # Ignore rollback errors
        except Exception as e:
            # If anything fails, log it but continue
            print(f"Warning: Error during session teardown: {e}")
        finally:
            # Always remove the session to clear connection state
            # This is critical to prevent "transaction aborted" errors from persisting
            try:
                db.session.remove()
            except Exception as e:
                print(f"Warning: Error removing session: {e}")
    jwt.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'routes1.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Error handler for file upload size limit (413 Request Entity Too Large)
    @app.errorhandler(413)
    def request_entity_too_large(error):
        from flask import redirect, url_for, flash
        from flask_login import current_user
        
        # Try to redirect back with error message
        if current_user.is_authenticated:
            flash('File upload is too large. Maximum file size is 50MB. Please compress or resize your image and try again.', 'error')
            # Try to redirect to the previous page or writer profile
            try:
                return redirect(url_for('writer.writer_profile'))
            except:
                return redirect('/')
        return 'File upload is too large. Maximum file size is 50MB. Please compress or resize your image and try again.', 413

    # Add logging for all requests at app level
    @app.before_request
    def log_request():
        try:
            # File logging (existing)
            with open("visits.txt", "a") as f:
                # Get current time in a more readable format
                now = datetime.now(timezone.utc)
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
                
                # Get user agent and extract browser info
                user_agent = request.headers.get('User-Agent', 'Unknown')
                browser = "Unknown"
                if 'Chrome' in user_agent:
                    browser = "Chrome"
                elif 'Firefox' in user_agent:
                    browser = "Firefox"
                elif 'Safari' in user_agent:
                    browser = "Safari"
                elif 'Edge' in user_agent:
                    browser = "Edge"
                elif 'curl' in user_agent:
                    browser = "curl"
                elif 'Norton' in user_agent:
                    browser = "Norton"
                
                # Get device type
                device = "Desktop"
                if 'Mobile' in user_agent or 'Android' in user_agent:
                    device = "Mobile"
                elif 'iPhone' in user_agent or 'iPad' in user_agent:
                    device = "Mobile"
                
                # Format the log entry in a more readable way
                f.write(f"[{timestamp}] {request.method} {request.path}\n")
                f.write(f"    IP: {request.remote_addr}\n")
                f.write(f"    Browser: {browser}\n")
                f.write(f"    Device: {device}\n")
                f.write(f"    User-Agent: {user_agent}\n")
                f.write("-" * 80 + "\n")
            
            # Database analytics logging (new)
            try:
                from .models import PageAnalytics, db
                from flask_login import current_user
                
                # Skip static files and admin endpoints (including analytics)
                if not request.path.startswith('/static') and not request.path.startswith('/_analytics') and request.path != '/analytics':
                    # Only log non-static pages to avoid database bloat
                    analytics = PageAnalytics(
                        path=request.path,
                        method=request.method,
                        ip_address=request.remote_addr,
                        browser=browser,
                        device=device,
                        user_agent=user_agent[:500] if len(user_agent) > 500 else user_agent,  # Limit length
                        user_id=current_user.user_id if current_user.is_authenticated else None,
                        is_authenticated=current_user.is_authenticated,
                        referer=request.referrer[:500] if request.referrer and len(request.referrer) > 500 else request.referrer
                    )
                    db.session.add(analytics)
                    
                    # Commit all analytics (database handles performance)
                    db.session.commit()
            except Exception as db_ex:
                # Don't fail the request if analytics fails
                print(f"Analytics logging error: {db_ex}")
                # Rollback on error
                try:
                    db.session.rollback()
                except:
                    pass
                
        except Exception as ex:
            print("Exception occurred while logging: ", ex)

    with app.app_context():
        # Import and register blueprints
        from .routes import bp 
        from .routes1 import bp1 
        from .routes2 import bp2
        from .blog import blog
        from .uprofile import prof
        from .playlist2 import play
        from .artists import music
        from .artist import art
        from .writer import writer
        from .book import book
        from .news_routes import news_bp
        from .book_platform_integration import init_book_platform
        from .analytics import analytics_bp

        app.register_blueprint(music, url_prefix="/music")
        app.register_blueprint(writer, url_prefix="/writer")
        app.register_blueprint(bp)
        app.register_blueprint(bp1, url_prefix='/routes1')
        app.register_blueprint(bp2, url_prefix='/routes2')
        app.register_blueprint(blog, url_prefix='/blog')
        app.register_blueprint(prof, url_prefix='/prof')
        app.register_blueprint(play, url_prefix='/playlist2')
        app.register_blueprint(art, url_prefix='/art')
        app.register_blueprint(book, url_prefix='/book')
        app.register_blueprint(news_bp, url_prefix='/routes2/news')
        app.register_blueprint(analytics_bp)
        
        # Initialize book platform
        app, socketio = init_book_platform(app)
        
        # Apply performance optimizations (temporarily disabled for testing)
        # from .performance_optimizer import optimize_app_performance
        # optimize_app_performance(app)

        # Ensure tables exist
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]
        if missing_tables:
            db.create_all()

    return app, socketio
