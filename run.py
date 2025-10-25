
from flask import Flask
from flask_migrate import Migrate
from glconnect import create_app, db
from glconnect.models import *

app, socketio = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)

