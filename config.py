import os

class Config:
    # TODO:
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///xts_allocator.db')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')

    DATABASE_URL = "sqlite:///xts_allocator.db"
