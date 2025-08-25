"""
Configuration utilities and validation helpers
Provides additional fallback mechanisms and configuration validation
"""

import os
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration values and provides fallback mechanisms"""
    
    @staticmethod
    def validate_url(url: str, scheme_required: bool = True) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            if scheme_required and not parsed.scheme:
                return False
            if not parsed.netloc and not parsed.path:
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_port(port: Any) -> bool:
        """Validate port number"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def get_environment_with_fallback() -> str:
        """Get environment with multiple fallback options"""
        env = os.getenv('ENVIRONMENT') or os.getenv('ENV') or os.getenv('NODE_ENV')
        
        if env:
            env = env.lower()
            # Normalize common environment names
            if env in ['dev', 'develop']:
                return 'development'
            elif env in ['prod', 'production']:
                return 'production'
            elif env in ['stage', 'staging']:
                return 'staging'
            elif env in ['test', 'testing']:
                return 'testing'
            return env
        
        # Default fallback
        return 'development'
    
    @staticmethod
    def build_url_with_fallbacks(
        protocol: str = 'http',
        host: str = 'localhost',
        port: Optional[int] = None,
        env_prefix: str = '',
        default_ports: Dict[str, int] = None
    ) -> str:
        """Build URL with fallback mechanisms"""
        if default_ports is None:
            default_ports = {
                'development': 8000 if protocol in ['http', 'ws'] else 8443,
                'staging': 80 if protocol == 'http' else 443,
                'production': 80 if protocol == 'http' else 443
            }
        
        # Try to get from environment variables with various patterns
        possible_env_vars = [
            f"{env_prefix}URL",
            f"{env_prefix}_URL",
            f"{protocol.upper()}_{env_prefix}URL",
            f"{protocol.upper()}_{env_prefix}_URL",
        ]
        
        for env_var in possible_env_vars:
            if env_var and os.getenv(env_var):
                url = os.getenv(env_var)
                if ConfigValidator.validate_url(url):
                    return url
        
        # Build from components
        if not port:
            env = ConfigValidator.get_environment_with_fallback()
            port = default_ports.get(env, 8000)
        
        # Handle WebSocket protocols
        if protocol == 'ws':
            if port == 443:
                protocol = 'wss'
        elif protocol == 'http':
            if port == 443:
                protocol = 'https'
        
        return f"{protocol}://{host}:{port}"
    
    @staticmethod
    def get_cors_origins_with_fallbacks(frontend_url: str, environment: str) -> List[str]:
        """Generate CORS origins with fallback patterns"""
        origins = [frontend_url]
        
        # Parse the frontend URL to extract components
        parsed = urlparse(frontend_url)
        
        if environment == 'development':
            # Add common development ports and hosts
            development_origins = [
                'http://localhost:8080',
                'http://127.0.0.1:8080',
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:5173',  # Vite dev server
                'http://127.0.0.1:5173',
            ]
            
            # Add with different ports if using localhost
            if 'localhost' in parsed.netloc or '127.0.0.1' in parsed.netloc:
                base_host = 'localhost' if 'localhost' in parsed.netloc else '127.0.0.1'
                for port in [3000, 5173, 8080, 8081, 8082]:
                    development_origins.extend([
                        f"http://{base_host}:{port}",
                        f"https://{base_host}:{port}",
                    ])
            
            origins.extend(development_origins)
        
        elif environment in ['staging', 'production']:
            # Add secure variants
            if parsed.scheme == 'http':
                secure_url = frontend_url.replace('http://', 'https://', 1)
                origins.append(secure_url)
            
            # Add without port if custom port is used
            if ':' in parsed.netloc and parsed.netloc.split(':')[1] not in ['80', '443']:
                host_only = parsed.netloc.split(':')[0]
                origins.extend([
                    f"http://{host_only}",
                    f"https://{host_only}",
                ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_origins = [x for x in origins if not (x in seen or seen.add(x))]
        
        return unique_origins
    
    @staticmethod
    def validate_configuration(config_dict: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate configuration and return validation results"""
        errors = []
        warnings = []
        
        # Validate URLs
        url_fields = ['FRONTEND_URL', 'BACKEND_URL', 'WEBSOCKET_URL', 'DATABASE_URL']
        for field in url_fields:
            if field in config_dict:
                if not ConfigValidator.validate_url(config_dict[field]):
                    errors.append(f"Invalid URL format for {field}: {config_dict[field]}")
        
        # Validate environment
        valid_environments = ['development', 'staging', 'production', 'testing']
        if 'ENVIRONMENT' in config_dict:
            if config_dict['ENVIRONMENT'] not in valid_environments:
                warnings.append(f"Unknown environment: {config_dict['ENVIRONMENT']}")
        
        # Validate SMTP configuration
        smtp_fields = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'FROM_EMAIL']
        smtp_provided = any(field in config_dict and config_dict[field] for field in smtp_fields)
        if smtp_provided:
            for field in smtp_fields:
                if field not in config_dict or not config_dict[field]:
                    errors.append(f"Missing required SMTP configuration: {field}")
            
            if 'SMTP_PORT' in config_dict and not ConfigValidator.validate_port(config_dict['SMTP_PORT']):
                errors.append(f"Invalid SMTP port: {config_dict['SMTP_PORT']}")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }


def get_fallback_configuration() -> Dict[str, str]:
    """Get fallback configuration values"""
    env = ConfigValidator.get_environment_with_fallback()
    
    return {
        'ENVIRONMENT': env,
        'FRONTEND_URL': ConfigValidator.build_url_with_fallbacks('http', 'localhost', 8080, 'FRONTEND'),
        'BACKEND_URL': ConfigValidator.build_url_with_fallbacks('http', 'localhost', 8000, 'BACKEND'),
        'WEBSOCKET_URL': ConfigValidator.build_url_with_fallbacks('ws', 'localhost', 8000, 'WEBSOCKET'),
        'DATABASE_URL': os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/erc_youth_db'),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production'),
    }


def apply_fallback_config(current_config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply fallback values to current configuration"""
    fallback_config = get_fallback_configuration()
    
    for key, fallback_value in fallback_config.items():
        if key not in current_config or not current_config[key]:
            current_config[key] = fallback_value
            logger.info(f"Applied fallback value for {key}")
    
    return current_config