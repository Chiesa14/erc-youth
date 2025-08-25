"""
Environment Configuration Manager
Handles loading environment-specific configurations with proper fallbacks
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class EnvConfigManager:
    """Manages environment-specific configuration loading with fallbacks"""
    
    def __init__(self, env: Optional[str] = None):
        self.env = env or os.getenv('ENVIRONMENT', 'development')
        self.loaded_files = []
        self.load_env_configs()
    
    def load_env_configs(self):
        """Load environment configurations with fallback chain"""
        # Define the loading order (most specific to least specific)
        config_files = [
            f'.env.{self.env}',      # Environment-specific config
            '.env.local',            # Local overrides (not in version control)
            '.env',                  # Default config
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                load_dotenv(config_file, override=False)  # Don't override already set values
                self.loaded_files.append(config_file)
                logger.info(f"Loaded configuration from: {config_file}")
        
        if not self.loaded_files:
            logger.warning("No environment configuration files found, using system environment variables only")
    
    def get_loaded_files(self) -> list:
        """Get list of loaded configuration files"""
        return self.loaded_files.copy()
    
    def validate_required_vars(self, required_vars: list) -> bool:
        """Validate that all required environment variables are set"""
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        return True
    
    def get_url_config(self) -> dict:
        """Get URL configuration with fallbacks"""
        return {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:8080'),
            'backend_url': os.getenv('BACKEND_URL', 'http://localhost:8000'),
            'websocket_url': os.getenv('WEBSOCKET_URL', 'ws://localhost:8000'),
        }
    
    @staticmethod
    def get_cors_origins(frontend_url: str) -> list:
        """Generate CORS origins based on frontend URL"""
        origins = [frontend_url]
        
        # Add common localhost variants for development
        if 'localhost' in frontend_url or '127.0.0.1' in frontend_url:
            origins.extend([
                'http://localhost:8080',
                'http://127.0.0.1:8080',
                'http://localhost:3000',  # Common React dev port
                'http://127.0.0.1:3000',
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in origins if not (x in seen or seen.add(x))]


# Initialize the configuration manager
env_manager = EnvConfigManager()

# Validate critical configuration
required_vars = [
    'DATABASE_URL',
    'SECRET_KEY',
    'FRONTEND_URL',
    'BACKEND_URL',
    'WEBSOCKET_URL'
]

if not env_manager.validate_required_vars(required_vars):
    logger.critical("Critical configuration missing! Please check your environment configuration.")
    # In production, you might want to raise an exception here