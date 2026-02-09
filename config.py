"""
Configuration management for XTS Allocator Server.
Supports SQLite (development) and PostgreSQL (production).
"""

import os
from urllib.parse import quote_plus


class Config:
    """Base configuration."""
    
    # Environment mode: test, development, production
    MODE = os.environ.get("XTS_MODE", "development")  # test, development, production
    
    # Database configuration
    DB_TYPE = os.environ.get("DB_TYPE", "sqlite")  # sqlite or postgresql
    
    # SQLite configuration (development and test)
    SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH", 
                                     "xts_allocator_test.db" if MODE == "test" else "xts_allocator.db")
    
    # Test database (always SQLite for easy reset)
    TEST_DB_PATH = os.environ.get("TEST_DB_PATH", "xts_allocator_test.db")
    
    # PostgreSQL configuration (production)
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "xts_allocator")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "xts_allocator")
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "xts-allocator-dev-secret-change-in-prod")
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # CORS configuration
    CORS_ENABLED = os.environ.get("CORS_ENABLED", "true").lower() == "true"
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
    
    # Server configuration
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "logs/xts_allocator.log")
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    
    # Background task intervals (seconds)
    EXPIRY_CHECK_INTERVAL = int(os.environ.get("EXPIRY_CHECK_INTERVAL", "60"))
    
    # Test execution limits
    TEST_MAX_DURATION_MINUTES = int(os.environ.get("TEST_MAX_DURATION_MINUTES", "240"))  # 4 hours
    TEST_HEARTBEAT_TIMEOUT_MINUTES = int(os.environ.get("TEST_HEARTBEAT_TIMEOUT_MINUTES", "15"))
    
    # Legacy compatibility
    DATABASE_URL = None  # Will be set by get_database_url()
    
    @classmethod
    def get_database_url(cls, echo: bool = True) -> str:
        """
        Get database URL based on DB_TYPE.
        
        Args:
            echo: Whether to enable SQLAlchemy echo (SQL logging)
            
        Returns:
            SQLAlchemy database URL
        """
        if cls.DB_TYPE == "postgresql":
            # URL-encode password to handle special characters
            password = quote_plus(cls.POSTGRES_PASSWORD) if cls.POSTGRES_PASSWORD else ""
            
            if password:
                url = (
                    f"postgresql://{cls.POSTGRES_USER}:{password}"
                    f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
                )
            else:
                url = (
                    f"postgresql://{cls.POSTGRES_USER}"
                    f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
                )
            
            return url
        else:
            # Default to SQLite
            return f"sqlite:///{cls.SQLITE_DB_PATH}"
    
    @classmethod
    def validate(cls) -> list:
        """
        Validate configuration and return list of warnings/errors.
        
        Returns:
            List of validation messages
        """
        issues = []
        
        # Check JWT secret in production
        if not cls.DEBUG and cls.JWT_SECRET_KEY == "xts-allocator-dev-secret-change-in-prod":
            issues.append("WARNING: Using default JWT secret key in production!")
        
        # Check PostgreSQL password
        if cls.DB_TYPE == "postgresql" and not cls.POSTGRES_PASSWORD:
            issues.append("WARNING: PostgreSQL password not set!")
        
        # Check CORS in production
        if not cls.DEBUG and cls.CORS_ORIGINS == ["*"]:
            issues.append("WARNING: CORS allows all origins in production!")
        
        return issues
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding secrets)."""
        print("=" * 60)
        print("XTS Allocator Server Configuration")
        print("=" * 60)
        print(f"Database Type:     {cls.DB_TYPE}")
        if cls.DB_TYPE == "sqlite":
            print(f"SQLite Path:       {cls.SQLITE_DB_PATH}")
        else:
            print(f"PostgreSQL Host:   {cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}")
            print(f"PostgreSQL DB:     {cls.POSTGRES_DB}")
            print(f"PostgreSQL User:   {cls.POSTGRES_USER}")
        print(f"Server:            {cls.HOST}:{cls.PORT}")
        print(f"Debug Mode:        {cls.DEBUG}")
        print(f"CORS Enabled:      {cls.CORS_ENABLED}")
        print(f"CORS Origins:      {', '.join(cls.CORS_ORIGINS)}")
        print(f"Rate Limiting:     {cls.RATE_LIMIT_ENABLED}")
        print(f"Log Level:         {cls.LOG_LEVEL}")
        print("=" * 60)
        
        # Print validation issues
        issues = cls.validate()
        if issues:
            print("\n⚠️  Configuration Issues:")
            for issue in issues:
                print(f"  - {issue}")
            print()


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DB_TYPE = "sqlite"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    DB_TYPE = "postgresql"
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://xts-allocator.example.com").split(",")


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    DB_TYPE = "sqlite"
    SQLITE_DB_PATH = ":memory:"  # In-memory database for tests


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get("XTS_ENV", "development").lower()
    
    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestingConfig
    else:
        return DevelopmentConfig


# Active configuration
config = get_config()

# Set legacy DATABASE_URL for backward compatibility
Config.DATABASE_URL = config.get_database_url()

