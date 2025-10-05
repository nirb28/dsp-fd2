"""
APISIX Client - Main Entry Point
Composed client using manager pattern for better organization
"""

import logging
from typing import Dict, Any
from datetime import datetime
import httpx

from .routes import RouteManager
from .upstreams import UpstreamManager
from .services import ServiceManager
from .consumers import ConsumerManager
from .global_rules import GlobalRulesManager
from .manifest_config import ManifestConfigurator
from .plugins import PluginBuilder

logger = logging.getLogger(__name__)


class APISIXClient:
    """
    Main APISIX client using composition pattern
    
    This client delegates operations to specialized managers:
    - RouteManager: Route CRUD operations
    - UpstreamManager: Upstream CRUD operations
    - ServiceManager: Service CRUD operations
    - ConsumerManager: Consumer CRUD operations
    - GlobalRulesManager: Global plugin rules
    - ManifestConfigurator: Manifest-based configuration
    - PluginBuilder: Plugin configuration helpers
    """
    
    def __init__(self, admin_url: str, admin_key: str):
        self.admin_url = admin_url.rstrip('/')
        self.admin_key = admin_key
        self.headers = {
            "X-API-KEY": admin_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize managers
        self.routes = RouteManager(self.admin_url, self.headers, self.client)
        self.upstreams = UpstreamManager(self.admin_url, self.headers, self.client)
        self.services = ServiceManager(self.admin_url, self.headers, self.client)
        self.consumers = ConsumerManager(self.admin_url, self.headers, self.client)
        self.global_rules = GlobalRulesManager(self.admin_url, self.headers, self.client)
        
        # Initialize manifest configurator
        self.manifest_config = ManifestConfigurator(
            self.routes,
            self.upstreams,
            self.services,
            self.consumers,
            self.global_rules
        )
        
        # Plugin builder for convenience
        self.plugins = PluginBuilder()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    # Route operations (delegated)
    async def create_route(self, route):
        """Create a new route in APISIX"""
        return await self.routes.create_route(route)
    
    async def get_route(self, route_id: str):
        """Get a specific route from APISIX"""
        return await self.routes.get_route(route_id)
    
    async def list_routes(self):
        """List all routes in APISIX"""
        return await self.routes.list_routes()
    
    async def delete_route(self, route_id: str):
        """Delete a route from APISIX"""
        return await self.routes.delete_route(route_id)
    
    # Upstream operations (delegated)
    async def create_upstream(self, upstream):
        """Create a new upstream in APISIX"""
        return await self.upstreams.create_upstream(upstream)
    
    async def get_upstream(self, upstream_id: str):
        """Get a specific upstream from APISIX"""
        return await self.upstreams.get_upstream(upstream_id)
    
    async def list_upstreams(self):
        """List all upstreams in APISIX"""
        return await self.upstreams.list_upstreams()
    
    async def delete_upstream(self, upstream_id: str):
        """Delete an upstream from APISIX"""
        return await self.upstreams.delete_upstream(upstream_id)
    
    # Service operations (delegated)
    async def create_service(self, service):
        """Create a new service in APISIX"""
        return await self.services.create_service(service)
    
    async def list_services(self):
        """List all services in APISIX"""
        return await self.services.list_services()
    
    async def delete_service(self, service_id: str):
        """Delete a service from APISIX"""
        return await self.services.delete_service(service_id)
    
    # Consumer operations (delegated)
    async def create_consumer(self, consumer):
        """Create a new consumer in APISIX"""
        return await self.consumers.create_consumer(consumer)
    
    async def get_consumer(self, username: str):
        """Get a specific consumer from APISIX"""
        return await self.consumers.get_consumer(username)
    
    async def list_consumers(self):
        """List all consumers in APISIX"""
        return await self.consumers.list_consumers()
    
    async def delete_consumer(self, username: str):
        """Delete a consumer from APISIX"""
        return await self.consumers.delete_consumer(username)
    
    # Global rules operations (delegated)
    async def get_global_rules(self):
        """Get global plugin rules"""
        return await self.global_rules.get_global_rules()
    
    async def set_global_rule(self, rule_id: str, plugins: Dict[str, Any]):
        """Set a global plugin rule"""
        return await self.global_rules.set_global_rule(rule_id, plugins)
    
    # Manifest configuration operations (delegated)
    async def configure_from_manifest(self, manifest: Dict[str, Any]):
        """Configure APISIX from Control Tower manifest"""
        return await self.manifest_config.configure_from_manifest(manifest)
    
    async def cleanup_project_resources(self, project_id: str):
        """Clean up all APISIX resources for a specific project"""
        return await self.manifest_config.cleanup_project_resources(project_id)
    
    async def list_project_resources(self, project_id: str):
        """List all APISIX resources for a specific project"""
        return await self.manifest_config.list_project_resources(project_id)
    
    # Plugin builder helpers (for backward compatibility)
    def build_jwt_plugin(self, key: str, secret: str, algorithm: str = "HS256", exp: int = 3600):
        """Build JWT authentication plugin configuration"""
        return self.plugins.build_jwt_plugin(key, secret, algorithm, exp)
    
    def build_rate_limit_plugin(self, rate: int, burst: int, key_type: str = "var", key: str = "remote_addr"):
        """Build rate limiting plugin configuration"""
        return self.plugins.build_rate_limit_plugin(rate, burst, key_type, key)
    
    def build_cors_plugin(self, origins: str = "*", methods: str = "*", headers: str = "*"):
        """Build CORS plugin configuration"""
        return self.plugins.build_cors_plugin(origins, methods, headers)
    
    def build_prometheus_plugin(self):
        """Build Prometheus metrics plugin configuration"""
        return self.plugins.build_prometheus_plugin()
    
    def build_logger_plugin(self, uri: str, batch_max_size: int = 1000):
        """Build HTTP logger plugin configuration"""
        return self.plugins.build_logger_plugin(uri, batch_max_size)
    
    def build_langfuse_plugin(
        self,
        public_key: str,
        secret_key: str,
        host: str = "https://cloud.langfuse.com",
        **kwargs
    ):
        """Build Langfuse observability plugin configuration"""
        return self.plugins.build_langfuse_plugin(public_key, secret_key, host, **kwargs)
    
    def build_combined_observability_plugins(
        self,
        langfuse_public_key: str,
        langfuse_secret_key: str,
        **kwargs
    ):
        """Build combined observability plugins including Langfuse"""
        return self.plugins.build_combined_observability_plugins(
            langfuse_public_key,
            langfuse_secret_key,
            **kwargs
        )
    
    # Health check
    async def health_check(self) -> Dict[str, Any]:
        """Check APISIX health status"""
        try:
            response = await self.client.get(
                f"{self.admin_url}/apisix/admin/routes",
                headers=self.headers,
                timeout=5.0
            )
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "admin_api_reachable": response.status_code == 200
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
