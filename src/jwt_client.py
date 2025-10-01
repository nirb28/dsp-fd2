"""
JWT Client for DSP AI JWT Service Integration
Handles token generation, validation, and consumer management
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class JWTClient:
    """Client for interacting with DSP AI JWT service"""
    
    def __init__(self, jwt_service_url: str, default_username: str = "admin", default_password: str = "dspsa_p@ssword"):
        """
        Initialize JWT client
        
        Args:
            jwt_service_url: Base URL of the JWT service (e.g., http://localhost:5000)
            default_username: Default username for token generation
            default_password: Default password for token generation
        """
        self.jwt_service_url = jwt_service_url.rstrip('/')
        self.default_username = default_username
        self.default_password = default_password
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def generate_token(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate JWT token from the JWT service
        
        Args:
            username: Username for authentication (uses default if not provided)
            password: Password for authentication (uses default if not provided)
            api_key: Optional API key for additional claims
            custom_secret: Optional custom secret for token signing
            
        Returns:
            Dictionary with access_token, refresh_token, and token metadata
        """
        try:
            payload = {
                "username": username or self.default_username,
                "password": password or self.default_password
            }
            
            if api_key:
                payload["api_key"] = api_key
            
            if custom_secret:
                payload["secret"] = custom_secret
            
            response = await self.client.post(
                f"{self.jwt_service_url}/token",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully generated JWT token for user: {username or self.default_username}")
                return {
                    "success": True,
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "token_type": data.get("token_type", "Bearer"),
                    "expires_in": data.get("expires_in"),
                    "custom_secret_used": data.get("custom_secret_used", False)
                }
            else:
                error_msg = f"Failed to generate token: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            error_msg = f"Error generating token: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dictionary with validation result and decoded claims
        """
        try:
            response = await self.client.get(
                f"{self.jwt_service_url}/protected",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "identity": data.get("logged_in_as"),
                    "claims": data
                }
            else:
                return {
                    "valid": False,
                    "error": f"Token validation failed: {response.status_code}",
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error validating token: {str(e)}"
            }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary with new access token
        """
        try:
            response = await self.client.post(
                f"{self.jwt_service_url}/refresh",
                headers={"Authorization": f"Bearer {refresh_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "access_token": data.get("access_token")
                }
            else:
                return {
                    "success": False,
                    "error": f"Token refresh failed: {response.status_code}",
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error refreshing token: {str(e)}"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check JWT service health
        
        Returns:
            Dictionary with health status
        """
        try:
            response = await self.client.get(
                f"{self.jwt_service_url}/",
                timeout=5.0
            )
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service_reachable": response.status_code == 200
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def configure_apisix_consumer(
        self,
        project_id: str,
        jwt_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate APISIX consumer configuration from JWT config module
        
        Args:
            project_id: Project identifier
            jwt_config: JWT configuration from manifest
            
        Returns:
            Dictionary with consumer configuration for APISIX
        """
        consumer_username = f"{project_id.replace('-', '_')}_consumer"
        
        # Extract JWT configuration
        secret_key = jwt_config.get("secret_key", "your-secret-key")
        algorithm = jwt_config.get("algorithm", "HS256")
        
        return {
            "username": consumer_username,
            "desc": f"JWT consumer for project: {project_id}",
            "plugins": {
                "jwt-auth": {
                    "key": f"{project_id}-key",
                    "secret": secret_key,
                    "algorithm": algorithm
                }
            }
        }
    
    def get_jwt_plugin_config(
        self,
        jwt_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate APISIX JWT plugin configuration from JWT config module
        
        Args:
            jwt_config: JWT configuration from manifest
            
        Returns:
            Dictionary with JWT plugin configuration
        """
        return {
            "jwt-auth": {
                "header": "Authorization",
                "query": "jwt",
                "cookie": "jwt",
                "hide_credentials": False
            }
        }
