import os
import json
import re
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

# Load configuration from environment variables first, then fall back to glconfig.json
config = {}

# Try environment variables first
env_config = {
    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    "OPENAI_AI_KEY": os.getenv("OPENAI_AI_KEY"),
    "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json"),
    "DB_URL": os.getenv("DB_URL"),
    "RECAPTCHAPUB": os.getenv("RECAPTCHAPUB"),
    "RECAPTCHAPRIV": os.getenv("RECAPTCHAPRIV")
}

# Check if we have any environment variables set
if any(env_config.values()):
    print("DEBUG: Using environment variables for configuration")
    config = env_config
else:
    print("DEBUG: No environment variables found, trying glconfig.json")
    # Fall back to glconfig.json if no environment variables are set
    try:
        with open('/etc/glconfig.json') as json_file:
            config = json.load(json_file)
        print("DEBUG: Loaded configuration from glconfig.json")
    except FileNotFoundError:
        print("DEBUG: glconfig.json not found, using environment variables with defaults")
        config = env_config
    except Exception as e:
        print(f"DEBUG: Error loading glconfig.json: {e}, using environment variables")
        config = env_config

# Debug: Check if Google credentials are loaded
# Get Google API key from glconfig.json
google_api_key = config.get("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY from glconfig.json: {google_api_key}")
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
    )

    # Secret key for sessions
    app.secret_key = os.urandom(24)

    # CKEditor configuration
    ckeditor = CKEditor() 
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['CKEDITOR_PKG_TYPE'] = 'full'

    # Mail and recaptcha configuration
    app.config['RECAPTCHA_PUBLIC_KEY'] = config.get('RECAPTCHAPUB')
    app.config['RECAPTCHA_PRIVATE_KEY'] = config.get('RECAPTCHAPRIV')

    # Database and JWT configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "abarayon"

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'routes1.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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

        # Ensure tables exist
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]
        if missing_tables:
            db.create_all()

    return app
