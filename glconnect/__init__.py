import os
import json
from flask import Flask, request
from .models import db, User
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect
from flask_login import LoginManager
from flask_mail import Mail
from flask_ckeditor import CKEditor
from flask_session import Session
from datetime import timedelta

# Initialize extensions
mail = Mail()
jwt = JWTManager()
login_manager = LoginManager()
ckeditor = CKEditor()

# Load configuration
with open('/etc/glconfig.json') as json_file:
    config = json.load(json_file)

def create_app():
    app = Flask(__name__)
    
    # Core configuration
    app.secret_key = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "abarayon"

    # Session configuration
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True

    # Mail & reCAPTCHA configuration
    app.config['RECAPTCHA_PUBLIC_KEY'] = config.get('RECAPTCHAPUB')
    app.config['RECAPTCHA_PRIVATE_KEY'] = config.get('RECAPTCHAPRIV')

    # CKEditor config
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['CKEDITOR_PKG_TYPE'] = 'full'

    # Initialize database and other extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    mail.init_app(app)
    Session(app)  # <-- must be AFTER db.init_app(app)

    login_manager.login_view = 'routes1.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # Register blueprints
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

        # Ensure all tables are created, including session table
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]
        if missing_tables:
            db.create_all()

    return app
