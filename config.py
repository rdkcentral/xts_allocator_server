import os

class Config:
    # TODO: Implement environment variable support for production deployments
    # Once implemented, uncomment these lines and remove hardcoded DATABASE_URL:
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///xts_allocator.db')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')

    DATABASE_URL = "sqlite:///xts_allocator.db"
