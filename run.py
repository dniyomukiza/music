
import os
import logging
import sys
from flask import Flask
from flask_migrate import Migrate
from glconnect import create_app, db
from glconnect.models import *

# Logging: always stdout; file only if writable (Docker bind mounts often deny appuser ./server.log)
_handlers = [logging.StreamHandler(sys.stdout)]
try:
    _fh = logging.FileHandler("server.log")
    _handlers.append(_fh)
except OSError:
    pass
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)

# Set specific loggers to appropriate levels
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
logging.getLogger('socketio').setLevel(logging.WARNING)  # Reduce SocketIO logs

app, socketio = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    # Set FLASK_ENV for local development if not already set
    if not os.getenv('FLASK_ENV') and not os.path.exists('/.dockerenv'):
        os.environ['FLASK_ENV'] = 'development'
    
    # Disable debug mode in production to prevent auto-reload issues
    # Debug mode causes 502 errors during code reloads when nginx tries to connect
    flask_env = os.getenv('FLASK_ENV', 'production')
    debug_mode = flask_env == 'development'
    
    # In Docker/production, disable reloader even if FLASK_ENV=development
    # to prevent 502 Bad Gateway errors during code reloads
    use_reloader = debug_mode and not os.path.exists('/.dockerenv')
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Flask app in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    logger.info(f"Reloader: {'ENABLED' if use_reloader else 'DISABLED'} (prevents 502 errors)")
    logger.info(f"App ready on http://0.0.0.0:5000")
    logger.info("Logging configured - logs will appear in console and server.log")
    
    socketio.run(
        app, 
        debug=debug_mode, 
        host="0.0.0.0", 
        port=5000, 
        allow_unsafe_werkzeug=True,
        use_reloader=use_reloader  # Disable in Docker to prevent 502 errors
    )

