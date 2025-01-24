import os
import time
from flask import Flask
from .models import db
from .voc import insert_data
from flask_jwt_extended import JWTManager 

jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_SECRET_KEY"] = "abarayon"

    # Initialize the database with the app
    db.init_app(app)
    jwt.init_app(app) 
    with app.app_context():
        # Register blueprints/routes
        from .routes import bp as routes_bp
        app.register_blueprint(routes_bp)

        # Create tables and insert data
        db.create_all()
        insert_data()

    return app

