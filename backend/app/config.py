import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://geolabeler:password@localhost:5432/geolabeler"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Celery / Redis
    # CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    # CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # File storage
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/geo-labeler/uploads")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff", "nc", "h5", "hdf5", "geotiff"}

    # AI service
    AI_MODEL_ENDPOINT = os.environ.get("AI_MODEL_ENDPOINT", "http://localhost:8001")
    AI_API_KEY = os.environ.get("AI_API_KEY", "")

    # DestinE integration
    DESTINE_API_URL = os.environ.get("DESTINE_API_URL", "https://destination-earth.eu/api")
    DESTINE_AUTH_URL = os.environ.get("DESTINE_AUTH_URL", "https://auth.destination-earth.eu")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
