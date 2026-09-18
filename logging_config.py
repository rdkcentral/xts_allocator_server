"""Logging configuration for XTS Allocator Server.

Provides structured logging with:
- Console handler for development (INFO level)
- Rotating file handler for production (INFO level)
- Automatic rotation at 10MB with 5 backup files
"""

import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(log_dir="logs", log_file="xts_allocator.log", level=logging.INFO):
    """
    Configure logging for the application.
    
    Args:
        log_dir: Directory for log files
        log_file: Name of the log file
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    
    # Create logger
    logger = logging.getLogger("xts_allocator")
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation (10MB max, 5 backups)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info("Logging configured successfully")
    logger.info(f"Log file: {log_path}")
    
    return logger


def get_logger():
    """Get the configured logger instance."""
    return logging.getLogger("xts_allocator")
