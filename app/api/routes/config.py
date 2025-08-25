"""
Configuration API endpoints
Provides frontend configuration and environment information
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.permissions import get_current_user
from app.models.user import User
from typing import Dict, Any

router = APIRouter()


@router.get("/frontend")
async def get_frontend_config():
    """Get frontend configuration (public endpoint)"""
    return settings.get_frontend_config()


@router.get("/environment")
async def get_environment_config():
    """Get environment configuration (public endpoint for basic info)"""
    return {
        "environment": settings.ENVIRONMENT,
        "backend_url": settings.BACKEND_URL,
        "websocket_url": settings.WEBSOCKET_URL,
    }


@router.get("/full")
async def get_full_config(current_user: User = Depends(get_current_user)):
    """Get full configuration details (authenticated users only)"""
    return settings.get_environment_config()


@router.get("/health")
async def config_health_check():
    """Health check endpoint for configuration system"""
    try:
        # Basic configuration validation
        required_configs = [
            settings.FRONTEND_URL,
            settings.BACKEND_URL,
            settings.WEBSOCKET_URL,
            settings.DATABASE_URL,
            settings.SECRET_KEY,
        ]
        
        missing_configs = [config for config in required_configs if not config]
        
        if missing_configs:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Missing required configurations: {len(missing_configs)} items"
            )
        
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "cors_origins_count": len(settings.CORS_ORIGINS),
            "loaded_config_files": settings.get_environment_config().get("loaded_config_files", [])
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration system error: {str(e)}"
        )


@router.get("/cors-origins")
async def get_cors_origins():
    """Get CORS origins configuration (useful for debugging)"""
    return {
        "cors_origins": settings.CORS_ORIGINS,
        "frontend_url": settings.FRONTEND_URL
    }