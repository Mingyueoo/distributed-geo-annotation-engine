import os
from app import create_app
from app.config import config
from app.extensions import celery  # noqa: F401 – needed to register tasks

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config.get(env, config["default"]))
app.app_context().push()
