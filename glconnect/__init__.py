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

# Diagnostic: capture env state BEFORE load_dotenv (to see if Docker injected vars)
_env_before = bool(os.getenv("GOOGLE_API_KEY"))

# Load .env from explicit paths (Docker CWD=/usr/src/appdir; local=project root)
# load_dotenv() with no args uses CWD - in Docker that's correct; but be explicit for reliability
_env_paths = [
    os.path.join(os.path.dirname(__file__), "..", ".env"),  # glconnect/../.env
    ".env",
    "/usr/src/appdir/.env",  # Docker WORKDIR
]
for _p in _env_paths:
    if os.path.isfile(_p):
        load_dotenv(_p)
        break
else:
    load_dotenv()  # fallback: CWD and parents

# Load configuration: env vars first, then fallback to glconfig.json if present
def _load_config():
    cfg = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "OPENAI_AI_KEY": os.getenv("OPENAI_AI_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json"),
        "DB_URL": os.getenv("DB_URL"),
        "RECAPTCHAPUB": os.getenv("RECAPTCHAPUB"),
        "RECAPTCHAPRIV": os.getenv("RECAPTCHAPRIV")
    }
    # Fallback: load from glconfig.json if env vars are empty (e.g. server with mounted config)
    for path in ["/etc/glconfig.json", "glconfig.json", os.path.join(os.path.dirname(__file__), "..", "glconfig.json")]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    file_cfg = json.load(f)
                if not cfg.get("GOOGLE_API_KEY") and file_cfg.get("GOOGLE_API_KEY"):
                    cfg["GOOGLE_API_KEY"] = file_cfg["GOOGLE_API_KEY"]
                if not cfg.get("GEMINI_API_KEY") and file_cfg.get("GEMINI_API_KEY"):
                    cfg["GEMINI_API_KEY"] = file_cfg["GEMINI_API_KEY"]
                break
            except Exception:
                pass
    return cfg

config = _load_config()

# Startup diagnostic: trace why keys might be missing
_cwd = os.getcwd()
_env_after = bool(os.getenv("GOOGLE_API_KEY"))
print(f"DEBUG: CWD={_cwd}")
print(f"DEBUG: .env in CWD: {os.path.isfile(os.path.join(_cwd, '.env'))}")
print(f"DEBUG: GOOGLE_API_KEY before load_dotenv: {'set' if _env_before else 'NOT SET (Docker did not inject)'}")
print(f"DEBUG: GOOGLE_API_KEY after load_dotenv: {'set' if _env_after else 'NOT SET'}")

# Push config into os.environ so modules that use os.getenv() get the values
if config.get("GOOGLE_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = config["GOOGLE_API_KEY"]
if config.get("GEMINI_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = config["GEMINI_API_KEY"]

google_api_key = config.get("GOOGLE_API_KEY")
gemini_api_key = config.get("GEMINI_API_KEY")
print(f"GOOGLE_API_KEY: {'(set)' if google_api_key else '(not set)'}")
print(f"GEMINI_API_KEY: {gemini_api_key[:20] + '...' if gemini_api_key else '(not set)'}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {config.get('GOOGLE_APPLICATION_CREDENTIALS', 'tts.json')}")

# Initialize extensions
mail = Mail()
jwt = JWTManager()
login_manager = LoginManager()

# Use the same config loaded above

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    CORS(app, origins=["https://glc.cool"], supports_credentials=True) # <-- ADD supports_credentials=True

    # Detect if running in local development
    is_local_dev = os.getenv('FLASK_ENV') == 'development' or not os.path.exists('/.dockerenv')
    
    # Secure session cookie configuration
    # For local development: use HTTP-compatible settings
    # For production: use HTTPS-required settings
    if is_local_dev:
        app.config.update(
            SESSION_COOKIE_SECURE=False,  # Allow cookies over HTTP in local dev
            SESSION_COOKIE_SAMESITE='Lax',  # Works with HTTP
            WTF_CSRF_ENABLED=True,  # Enable CSRF protection
            WTF_CSRF_TIME_LIMIT=None,  # No time limit for CSRF tokens in dev
        )
    else:
        app.config.update(
            SESSION_COOKIE_SECURE=True,  # Require HTTPS in production
            SESSION_COOKIE_SAMESITE='None',  # Cross-site cookies for production
            WTF_CSRF_ENABLED=True,
        )
    
    app.config.update(
        JWT_SECRET_KEY="abarayon",
        GEMINI_API_KEY=config.get("GEMINI_API_KEY"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,  # 2 GB max upload size
    )

    # Secret key for sessions (use fixed key for local dev to maintain sessions across restarts)
    if is_local_dev:
        app.secret_key = "local-dev-secret-key-change-in-production"  # Fixed key for local dev
    else:
        app.secret_key = os.urandom(24)  # Random key for production

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
            # Always rollback on exception OR if there's any uncommitted transaction
            # This prevents "transaction aborted" errors from persisting
            if exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass  # Ignore rollback errors
            else:
                # Even without an exception, check if transaction needs cleanup
                # Rollback any pending transaction to ensure clean state
                try:
                    # Check if session is in a bad state by attempting a rollback
                    # This is safe - rollback on a clean transaction is a no-op
                    db.session.rollback()
                except Exception:
                    # If rollback fails, the session is likely already in a bad state
                    # Force remove it to clear the connection
                    pass
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

    # Global 500 error handler - returns JSON for API routes
    @app.errorhandler(500)
    def handle_500_error(error):
        """Handle 500 errors globally and return JSON for API routes"""
        from flask import request, jsonify
        import traceback
        
        error_traceback = traceback.format_exc()
        
        # Check if this is an API request (JSON expected)
        is_api_request = (
            request.is_json or 
            '/purchase' in request.path or 
            request.path.startswith('/mybook/books/') or
            request.headers.get('Content-Type', '').startswith('application/json') or
            request.headers.get('Accept', '').startswith('application/json') or
            request.method == 'POST' and '/mybook/' in request.path
        )
        
        if is_api_request:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_traceback = traceback.format_exc()
            error_msg = str(error)
            
            # Log full technical details for debugging (server-side only)
            logger.error("=" * 80)
            logger.error("❌ GLOBAL 500 ERROR - Full Technical Details (for debugging)")
            logger.error("=" * 80)
            logger.error(f"Request Context:")
            logger.error(f"  - Path: {request.path}")
            logger.error(f"  - Method: {request.method}")
            logger.error(f"  - User: {request.remote_addr if request else 'N/A'}")
            logger.error(f"  - Headers: {dict(request.headers) if request else 'N/A'}")
            logger.error(f"Error Details:")
            logger.error(f"  - Error Type: {type(error).__name__}")
            logger.error(f"  - Error Message: {error_msg}")
            logger.error(f"  - Full Traceback:")
            logger.error(error_traceback)
            logger.error("=" * 80)
            # Also log with exc_info for stack trace in log handlers
            logger.error(f"500 error in {request.path}: {error_msg}", exc_info=True)
            
            # Return user-friendly error message without exposing technical details
            return jsonify({
                'success': False,
                'error': 'We encountered an unexpected error. Our team has been notified. Please try again in a moment.'
            }), 500
        
        # For non-API routes, let Flask handle it normally (will show HTML error page)
        raise error

    # Add transaction cleanup before each request to prevent "transaction aborted" errors
    @app.before_request
    def cleanup_transaction():
        """Clean up any aborted transactions before processing a new request"""
        try:
            # Rollback any pending/aborted transactions to ensure clean state
            # This prevents "transaction aborted" errors from previous requests
            db.session.rollback()
        except Exception:
            # If rollback fails, the session might be in a bad state
            # Remove it to force a fresh connection
            try:
                db.session.remove()
            except Exception:
                pass  # Ignore errors during cleanup
    
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
