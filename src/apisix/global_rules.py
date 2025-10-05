"""
APISIX Global Rules Manager
Handles global plugin rules
"""

import logging
from typing import Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class GlobalRulesManager:
    """Manager for APISIX global plugin rules"""
    
    def __init__(self, admin_url: str, headers: Dict[str, str], client: httpx.AsyncClient):
        self.admin_url = admin_url
        self.headers = headers
        self.client = client
    
    async def get_global_rules(self) -> List[Dict[str, Any]]:
        """Get global plugin rules"""
        response = await self.client.get(
            f"{self.admin_url}/apisix/admin/global_rules",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get global rules: {response.status_code}")
        
        data = response.json()
        return data.get("list", []) if "list" in data else []
    
    async def set_global_rule(self, rule_id: str, plugins: Dict[str, Any]) -> Dict[str, Any]:
        """Set a global plugin rule"""
        response = await self.client.put(
            f"{self.admin_url}/apisix/admin/global_rules/{rule_id}",
            json={"plugins": plugins},
            headers=self.headers
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to set global rule: {response.text}")
            raise Exception(f"Failed to set global rule: {response.status_code}")
        
        return response.json()
