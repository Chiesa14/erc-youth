from pydantic_settings import BaseSettings
from typing import List
import os

# Import our environment configuration manager
from app.core.env_config import env_manager

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str

    # URL Configuration with fallbacks
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://127.0.0.1:8080"
    BACKEND_URL: str = "http://localhost:8000"
    WEBSOCKET_URL: str = "ws://localhost:8000"
    
    # CORS origins - will be derived from frontend URLs
    CORS_ORIGINS: List[str] = []

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        # Apply environment-specific configuration before initializing parent
        url_config = env_manager.get_url_config()
        
        # Merge environment config with kwargs
        for key, value in url_config.items():
            if key.upper() not in kwargs:  # Don't override explicit kwargs
                kwargs[key.upper()] = value
        
        super().__init__(**kwargs)
        
        # Auto-populate CORS origins based on frontend URL after initialization
        if not self.CORS_ORIGINS:
            self.CORS_ORIGINS = env_manager.get_cors_origins(self.FRONTEND_URL)

    @property
    def frontend_change_password_url(self) -> str:
        """Get the full URL for the change password page"""
        return f"{self.FRONTEND_URL}/change-password"
    
    @property
    def websocket_chat_url(self) -> str:
        """Get the WebSocket chat URL pattern (without token)"""
        return f"{self.WEBSOCKET_URL}/chat/ws"
    
    @property
    def websocket_chat_url_with_token(self) -> str:
        """Get the WebSocket chat URL template with token placeholder"""
        return f"{self.WEBSOCKET_URL}/chat/ws?token={{token}}"

    def get_environment_config(self) -> dict:
        """Get environment-specific configuration as a dictionary"""
        return {
            "environment": self.ENVIRONMENT,
            "frontend_url": self.FRONTEND_URL,
            "backend_url": self.BACKEND_URL,
            "websocket_url": self.WEBSOCKET_URL,
            "websocket_chat_url": self.websocket_chat_url,
            "cors_origins": self.CORS_ORIGINS,
            "loaded_config_files": env_manager.get_loaded_files(),
        }
    
    def get_frontend_config(self) -> dict:
        """Get configuration that can be safely exposed to frontend"""
        return {
            "environment": self.ENVIRONMENT,
            "backend_url": self.BACKEND_URL,
            "websocket_url": self.WEBSOCKET_URL,
            "websocket_chat_url": self.websocket_chat_url,
        }

settings = Settings()
