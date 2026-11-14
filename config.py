import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'campusconnect-secret-key-prod-grade-2026')
    
    # Database configuration with PostgreSQL preferred, SQLite fallback
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        instance_dir = os.path.join(BASE_DIR, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'campusconnect.db')}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }
    
    # Upload limits and paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    
    # Campus Email Configuration
    CAMPUS_EMAIL_DOMAINS = os.environ.get('CAMPUS_EMAIL_DOMAINS', 'campusconnect.edu,university.edu,student.campusconnect.edu').split(',')
    CAMPUS_EMAIL_DOMAIN = os.environ.get('CAMPUS_EMAIL_DOMAIN', 'campusconnect.edu')
    
    # Mail server configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'CampusConnect Support <noreply@campusconnect.edu>')
    
    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_TIME_LIMIT = None  # Valid for session
    
    # SocketIO
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE')
    
    # Campus Coordinates for maps (Amrita Vishwa Vidyapeetham, Nagercoil Campus)
    CAMPUS_CENTER_LAT = float(os.environ.get('CAMPUS_CENTER_LAT', 8.22901))
    CAMPUS_CENTER_LNG = float(os.environ.get('CAMPUS_CENTER_LNG', 77.41539))
    CAMPUS_DEFAULT_ZOOM = int(os.environ.get('CAMPUS_DEFAULT_ZOOM', 17))

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SERVER_NAME = 'localhost'

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

