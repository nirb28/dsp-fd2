"""
APISIX Route Manager
Handles route CRUD operations
"""

import logging
from typing import Dict, Any, List
import httpx
from .models import APISIXRoute

logger = logging.getLogger(__name__)


class RouteManager:
    """Manager for APISIX route operations"""
    
    def __init__(self, admin_url: str, headers: Dict[str, str], client: httpx.AsyncClient):
        self.admin_url = admin_url
        self.headers = headers
        self.client = client
    
    async def create_route(self, route: APISIXRoute) -> Dict[str, Any]:
        """Create a new route in APISIX"""
        route_data = route.model_dump(exclude_none=True, exclude={"id"})
        
        url = f"{self.admin_url}/apisix/admin/routes"
        if route.id:
            url = f"{url}/{route.id}"
        
        response = await self.client.put(
            url,
            json=route_data,
            headers=self.headers
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create route: {response.text}")
            raise Exception(f"Failed to create route: {response.status_code}")
        
        return response.json()
    
    async def get_route(self, route_id: str) -> Dict[str, Any]:
        """Get a specific route from APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/routes/{route_id}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get route: {response.status_code}")
        
        return response.json()
    
    async def list_routes(self) -> List[Dict[str, Any]]:
        """List all routes in APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/routes",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to list routes: {response.status_code}")
        
        data = response.json()
        return data.get("list", []) if "list" in data else []
    
    async def delete_route(self, route_id: str) -> bool:
        """Delete a route from APISIX"""
        response = await self.client.delete(
            f"{self.admin_url}/apisix/admin/routes/{route_id}",
            headers=self.headers
        )
        
        return response.status_code == 200
