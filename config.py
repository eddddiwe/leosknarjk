import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Project base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Base configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Sync configuration
    SYNC_INTERVAL = 300  # 5 minutes
    
    # Backup configuration
    BACKUP_INTERVAL = 3600  # 1 hour
    BACKUP_DIR = 'backups'
    
    # Local SQLite database
    SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL', 'sqlite:///secure_db.sqlite')
    
    # Cloud PostgreSQL database
    CLOUD_DATABASE_URL = os.getenv('CLOUD_DATABASE_URL')
    
    # Device settings
    DEVICE_ID = os.getenv('DEVICE_ID', 'default')
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    # Use BASE_DIR to specify the database path in the project root and use the correct SQLite URL format
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(Config.BASE_DIR, 'dev.db')
    CLOUD_DATABASE_URI = None

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://user:password@host:port/dbname')
    CLOUD_DATABASE_URL = os.getenv('CLOUD_DATABASE_URL')
    
    # Production-specific settings
    SYNC_INTERVAL = 60  # 1 minute
    BACKUP_INTERVAL = 1800  # 30 minutes

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    CLOUD_DATABASE_URI = None
    
    # Testing-specific settings
    SYNC_INTERVAL = 10  # 10 seconds
    BACKUP_INTERVAL = 60  # 1 minute

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 