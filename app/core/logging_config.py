import logging
import logging.config
import os
from datetime import datetime

def setup_logging():
    """Setup centralized logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Define logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            },
            "json": {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file_info": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/app_info.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/app_error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "file_debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/app_debug.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": "INFO",
                "handlers": ["console", "file_info"]
            },
            "app": {  # Application logger
                "level": "DEBUG",
                "handlers": ["console", "file_info", "file_debug"],
                "propagate": False
            },
            "uvicorn": {  # Uvicorn logger
                "level": "INFO",
                "handlers": ["console", "file_info"],
                "propagate": False
            },
            "fastapi": {  # FastAPI logger
                "level": "INFO",
                "handlers": ["console", "file_info"],
                "propagate": False
            }
        }
    }
    
    # Apply the configuration
    logging.config.dictConfig(logging_config)
    
    # Set specific logger levels based on environment
    if os.getenv("ENVIRONMENT", "development") == "development":
        logging.getLogger("app").setLevel(logging.DEBUG)
        logging.getLogger("").setLevel(logging.DEBUG)
    
    # Log the startup
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration initialized successfully")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log files will be written to: {os.path.abspath('logs')}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name) 
