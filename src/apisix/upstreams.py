"""
APISIX Upstream Manager
Handles upstream CRUD operations
"""

import logging
from typing import Dict, Any, List
import httpx
from .models import APISIXUpstream

logger = logging.getLogger(__name__)


class UpstreamManager:
    """Manager for APISIX upstream operations"""
    
    def __init__(self, admin_url: str, headers: Dict[str, str], client: httpx.AsyncClient):
        self.admin_url = admin_url
        self.headers = headers
        self.client = client
    
    async def create_upstream(self, upstream: APISIXUpstream) -> Dict[str, Any]:
        """Create a new upstream in APISIX"""
        upstream_data = upstream.model_dump(exclude_none=True, exclude={"id"})
        
        url = f"{self.admin_url}/apisix/admin/upstreams"
        if upstream.id:
            url = f"{url}/{upstream.id}"
        
        response = await self.client.put(
            url,
            json=upstream_data,
            headers=self.headers
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create upstream: {response.text}")
            raise Exception(f"Failed to create upstream: {response.status_code}")
        
        return response.json()
    
    async def get_upstream(self, upstream_id: str) -> Dict[str, Any]:
        """Get a specific upstream from APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/upstreams/{upstream_id}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get upstream: {response.status_code}")
        
        return response.json()
    
    async def list_upstreams(self) -> List[Dict[str, Any]]:
        """List all upstreams in APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/upstreams",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to list upstreams: {response.status_code}")
        
        data = response.json()
        return data.get("list", []) if "list" in data else []
    
    async def delete_upstream(self, upstream_id: str) -> bool:
        """Delete an upstream from APISIX"""
        response = await self.client.delete(
            f"{self.admin_url}/apisix/admin/upstreams/{upstream_id}",
            headers=self.headers
        )
        
        return response.status_code == 200
