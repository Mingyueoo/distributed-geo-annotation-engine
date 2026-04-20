import os
from app import create_app
from app.config import config
from app.extensions import socketio

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config.get(env, config["default"]))

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config["DEBUG"],
    )
