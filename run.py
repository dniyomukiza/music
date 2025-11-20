
import os
from flask import Flask
from flask_migrate import Migrate
from glconnect import create_app, db
from glconnect.models import *

app, socketio = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    # Disable debug mode in production to prevent auto-reload issues
    # Debug mode causes 502 errors during code reloads when nginx tries to connect
    flask_env = os.getenv('FLASK_ENV', 'production')
    debug_mode = flask_env == 'development'
    
    # In Docker/production, disable reloader even if FLASK_ENV=development
    # to prevent 502 Bad Gateway errors during code reloads
    use_reloader = debug_mode and not os.path.exists('/.dockerenv')
    
    print(f"Starting Flask app in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    print(f"Reloader: {'ENABLED' if use_reloader else 'DISABLED'} (prevents 502 errors)")
    print(f"App ready on http://0.0.0.0:5000")
    
    socketio.run(
        app, 
        debug=debug_mode, 
        host="0.0.0.0", 
        port=5000, 
        allow_unsafe_werkzeug=True,
        use_reloader=use_reloader  # Disable in Docker to prevent 502 errors
    )

