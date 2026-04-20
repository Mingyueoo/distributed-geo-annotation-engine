from flask import Flask
from .config import Config
from .extensions import db, migrate, jwt, socketio, celery
from flask_cors import CORS


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, message_queue=app.config.get("CELERY_BROKER_URL"))

    # Register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.dataset_routes import dataset_bp
    from .routes.image_routes import image_bp
    from .routes.annotation_routes import annotation_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dataset_bp, url_prefix="/api/datasets")
    app.register_blueprint(image_bp, url_prefix="/api/images")
    app.register_blueprint(annotation_bp, url_prefix="/api/annotations")

    # Configure Celery
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    return app
