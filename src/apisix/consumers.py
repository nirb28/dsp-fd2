"""
APISIX Consumer Manager
Handles consumer CRUD operations
"""

import logging
from typing import Dict, Any, List
import httpx
from .models import APISIXConsumer

logger = logging.getLogger(__name__)


class ConsumerManager:
    """Manager for APISIX consumer operations"""
    
    def __init__(self, admin_url: str, headers: Dict[str, str], client: httpx.AsyncClient):
        self.admin_url = admin_url
        self.headers = headers
        self.client = client
    
    async def create_consumer(self, consumer: APISIXConsumer) -> Dict[str, Any]:
        """Create a new consumer in APISIX"""
        consumer_data = consumer.model_dump(exclude_none=True)
        
        response = await self.client.put(
            f"{self.admin_url}/apisix/admin/consumers/{consumer.username}",
            json=consumer_data,
            headers=self.headers
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create consumer: {response.text}")
            raise Exception(f"Failed to create consumer: {response.status_code}")
        
        return response.json()
    
    async def get_consumer(self, username: str) -> Dict[str, Any]:
        """Get a specific consumer from APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/consumers/{username}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get consumer: {response.status_code}")
        
        return response.json()
    
    async def list_consumers(self) -> List[Dict[str, Any]]:
        """List all consumers in APISIX"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/consumers",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to list consumers: {response.status_code}")
        
        data = response.json()
        return data.get("list", []) if "list" in data else []
    
    async def delete_consumer(self, username: str) -> bool:
        """Delete a consumer from APISIX"""
        response = await self.client.delete(
            f"{self.admin_url}/apisix/admin/consumers/{username}",
            headers=self.headers
        )
        
        return response.status_code == 200
