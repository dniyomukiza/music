import os
from flask import Flask
from .models import db, User
from .voc import insert_data
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
from flask_ckeditor import CKEditor

# Load environment variables
load_dotenv()

# Initialize extensions
mail = Mail()
jwt = JWTManager()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    ckeditor = CKEditor() 
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['CKEDITOR_PKG_TYPE'] = 'full'   
    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Database and JWT configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "abarayon"

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'routes1.login'

    # Register user_loader globally
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

        app.register_blueprint(music, url_prefix="/music")
        app.register_blueprint(bp)
        app.register_blueprint(bp1, url_prefix='/routes1')
        app.register_blueprint(bp2, url_prefix='/routes2')
        app.register_blueprint(blog, url_prefix='/blog')
        app.register_blueprint(prof, url_prefix='/prof')
        app.register_blueprint(play, url_prefix='/playlist2')
        app.register_blueprint(art, url_prefix='/art')
        # Ensure tables exist
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]
        if missing_tables:
            db.create_all()

    return app
