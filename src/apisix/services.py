"""
APISIX Service Manager
Handles service CRUD operations
"""

import logging
from typing import Dict, Any, List
import httpx
from .models import APISIXService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manager for APISIX service operations"""
    
    def __init__(self, admin_url: str, headers: Dict[str, str], client: httpx.AsyncClient):
        self.admin_url = admin_url
        self.headers = headers
        self.client = client
    
    async def create_service(self, service: APISIXService) -> Dict[str, Any]:
        """Create a new service in APISIX"""
        service_data = service.model_dump(exclude_none=True, exclude={"id"})
        
        url = f"{self.admin_url}/apisix/admin/services"
        if service.id:
            url = f"{url}/{service.id}"
        
        response = await self.client.put(
            url,
            json=service_data,
            headers=self.headers
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create service: {response.text}")
            raise Exception(f"Failed to create service: {response.status_code}")
        
        return response.json()
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """List all services in APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/services",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to list services: {response.status_code}")
        
        data = response.json()
        return data.get("list", []) if "list" in data else []
    
    async def delete_service(self, service_id: str) -> bool:
        """Delete a service from APISIX"""
        response = await self.client.delete(
            f"{self.admin_url}/apisix/admin/services/{service_id}",
            headers=self.headers
        )
        
        return response.status_code == 200
