import os
from flask import Flask
from .models import db, User
from .voc import insert_data
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect
from flask_login import LoginManager

# Initialize extensions outside of the create_app function
jwt = JWTManager()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "abarayon"
    
    # Initialize the database and JWTManager with the app
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'routes1.login'  # Define the route to redirect to when not authenticated
    
    # Register user_loader globally
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # Register blueprints/routes
        from .routes import bp as routes_bp
        app.register_blueprint(routes_bp)
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]
        if missing_tables:
            db.create_all()

    return app

