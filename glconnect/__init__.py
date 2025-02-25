import os
from flask import Flask
from .models import db
from .voc import insert_data
from flask_jwt_extended import JWTManager
from sqlalchemy import inspect

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
        # Check for missing tables and create only those
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        missing_tables = [table for table in db.metadata.tables.keys() if table not in existing_tables]

        if missing_tables:
            db.create_all()

    return app


