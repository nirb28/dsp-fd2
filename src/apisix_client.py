"""
APISIX Client for Front Door Integration
Handles APISIX route configuration and management based on Control Tower manifests
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class APISIXPlugin(BaseModel):
    """APISIX plugin configuration"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    priority: Optional[int] = None


class APISIXRoute(BaseModel):
    """APISIX route configuration"""
    id: Optional[str] = None
    name: str
    uri: str
    methods: List[str] = Field(default_factory=lambda: ["GET", "POST"])
    upstream: Optional[Dict[str, Any]] = None  # Inline upstream configuration
    upstream_id: Optional[str] = None
    service_id: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    host: Optional[str] = None
    priority: int = 0
    vars: Optional[List[List]] = None
    enable_websocket: bool = False


class APISIXUpstream(BaseModel):
    """APISIX upstream configuration"""
    id: Optional[str] = None
    name: str
    type: str = "roundrobin"
    nodes: Dict[str, int]
    timeout: Dict[str, int] = Field(
        default_factory=lambda: {"connect": 30, "send": 30, "read": 30}
    )
    retries: int = 1
    retry_timeout: int = 0
    pass_host: str = "pass"
    scheme: str = Field(default="https")  # Default to http, but can be overridden by manifest
    hash_on: Optional[str] = None


class APISIXService(BaseModel):
    """APISIX service configuration"""
    id: Optional[str] = None
    name: str
    desc: Optional[str] = None
    upstream_id: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    enable_websocket: bool = False


class APISIXConsumer(BaseModel):
    """APISIX consumer configuration"""
    username: str
    desc: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    group_id: Optional[str] = None


class APISIXClient:
    """Client for managing APISIX configurations"""
    
    def __init__(self, admin_url: str, admin_key: str):
        self.admin_url = admin_url.rstrip('/')
        self.admin_key = admin_key
        self.headers = {
            "X-API-KEY": admin_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    # Route Management
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
    
    # Upstream Management
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
    
    # Service Management
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
    
    # Consumer Management
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
    
    # Plugin Management
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
    
    # Helper Methods
    def build_jwt_plugin(
        self,
        key: str,
        secret: str,
        algorithm: str = "HS256",
        exp: int = 3600
    ) -> Dict[str, Any]:
        """Build JWT authentication plugin configuration"""
        return {
            "jwt-auth": {
                "key": key,
                "secret": secret,
                "algorithm": algorithm,
                "exp": exp,
                "header": "Authorization",
                "cookie": "jwt",
                "hide_credentials": True
            }
        }
    
    def build_rate_limit_plugin(
        self,
        rate: int,
        burst: int,
        key_type: str = "var",
        key: str = "remote_addr"
    ) -> Dict[str, Any]:
        """Build rate limiting plugin configuration"""
        return {
            "limit-req": {
                "rate": rate,
                "burst": burst,
                "key_type": key_type,
                "key": key,
                "rejected_code": 429,
                "rejected_msg": "Too many requests"
            }
        }
    
    def build_cors_plugin(
        self,
        origins: str = "*",
        methods: str = "*",
        headers: str = "*"
    ) -> Dict[str, Any]:
        """Build CORS plugin configuration"""
        return {
            "cors": {
                "allow_origins": origins,
                "allow_methods": methods,
                "allow_headers": headers,
                "expose_headers": "*",
                "max_age": 3600,
                "allow_credential": True
            }
        }
    
    def build_prometheus_plugin(self) -> Dict[str, Any]:
        """Build Prometheus metrics plugin configuration"""
        return {
            "prometheus": {
                "prefer_name": True
            }
        }
    
    def build_logger_plugin(
        self,
        uri: str,
        batch_max_size: int = 1000
    ) -> Dict[str, Any]:
        """Build HTTP logger plugin configuration"""
        return {
            "http-logger": {
                "uri": uri,
                "batch_max_size": batch_max_size,
                "inactive_timeout": 5,
                "buffer_duration": 60,
                "max_retry_count": 3,
                "retry_delay": 1,
                "include_req_body": True,
                "include_resp_body": False
            }
        }
    
    async def configure_from_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Configure APISIX routes and upstreams from Control Tower manifest
        
        Organization strategy:
        - Create a Service for each project/manifest
        - Create a Consumer for each project/manifest
        - Prefix all resources with project_id
        - Add descriptive metadata to identify source manifest
        """
        results = {
            "routes": [],
            "upstreams": [],
            "services": [],
            "consumers": [],
            "global_rules": [],
            "errors": []
        }
        
        # Extract project info for organization
        project_id = manifest.get("project_id", "unknown")
        project_name = manifest.get("project_name", "Unknown Project")
        environment = manifest.get("environment", "default")
        
        # Find APISIX gateway modules in manifest
        modules = manifest.get("modules", [])
        apisix_modules = []
        jwt_module = None
        
        for module in modules:
            if module.get("module_type") == "api_gateway" and "apisix" in module.get("name", "").lower():
                apisix_modules.append(module)
            elif module.get("module_type") == "jwt_config":
                jwt_module = module
        
        if not apisix_modules:
            results["errors"].append("No APISIX gateway module found in manifest")
            return results
        
        # Create a consumer for this project
        try:
            consumer_username = f"{project_id.replace('-', '_')}_consumer"
            consumer_desc = f"Consumer for project: {project_name} ({environment})"
            
            # Add JWT plugin if JWT module exists
            consumer_plugins = {}
            if jwt_module and jwt_module.get("config"):
                jwt_config = jwt_module.get("config", {})
                # Proper JWT auth plugin configuration for consumer
                consumer_plugins["jwt-auth"] = {
                    "key": f"{project_id}-key",
                    "secret": jwt_config.get("secret_key", "your-secret-key")
                }
            
            consumer = APISIXConsumer(
                username=consumer_username,
                desc=consumer_desc,
                plugins=consumer_plugins
            )
            result = await self.create_consumer(consumer)
            results["consumers"].append(result)
            logger.info(f"Created consumer: {consumer_username}")
        except Exception as e:
            error_msg = f"Failed to create consumer for {project_id}: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Create a service for this project to group all routes
        try:
            service_id = f"{project_id}-service"
            service_name = f"{project_id}-api-service"
            service_desc = f"API Service for {project_name} - Environment: {environment}"
            
            service = APISIXService(
                id=service_id,
                name=service_name,
                desc=service_desc,
                enable_websocket=False
            )
            
            result = await self.create_service(service)
            results["services"].append(result)
            logger.info(f"Created service: {service_name}")
        except Exception as e:
            error_msg = f"Failed to create service for {project_id}: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # Process all APISIX modules
        for apisix_module in apisix_modules:
            config = apisix_module.get("config", {})
            
            # Create upstreams with project prefix (from separate upstreams array)
            for upstream_config in config.get("upstreams", []):
                try:
                    # Add project prefix to upstream name and ID
                    original_name = upstream_config.get("name", "upstream")
                    upstream_config["name"] = f"{project_id}-{original_name}"
                    upstream_config["id"] = f"{project_id}-{original_name}"
                    
                    upstream = APISIXUpstream(**upstream_config)
                    result = await self.create_upstream(upstream)
                    results["upstreams"].append(result)
                    logger.info(f"Created upstream: {upstream.name}")
                except Exception as e:
                    error_msg = f"Failed to create upstream {upstream_config.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Extract and create inline upstreams from routes as separate resources
            upstream_id_mapping = {}  # Map original route name to upstream ID
            for route_config in config.get("routes", []):
                if "upstream" in route_config:
                    try:
                        original_route_name = route_config.get("name", "route")
                        upstream_data = route_config["upstream"].copy()
                        
                        # Create upstream with route-based naming
                        upstream_name = f"{original_route_name}-upstream"
                        upstream_id = f"{project_id}-{upstream_name}"
                        
                        upstream = APISIXUpstream(
                            id=upstream_id,
                            name=f"{project_id}-{upstream_name}",
                            type=upstream_data.get("type", "roundrobin"),
                            nodes=upstream_data.get("nodes", {}),
                            timeout=upstream_data.get("timeout", {"connect": 30, "send": 30, "read": 30}),
                            retries=upstream_data.get("retries", 1),
                            retry_timeout=upstream_data.get("retry_timeout", 0),
                            pass_host=upstream_data.get("pass_host", "pass"),
                            scheme=upstream_data.get("scheme", "https")
                        )
                        
                        result = await self.create_upstream(upstream)
                        results["upstreams"].append(result)
                        upstream_id_mapping[original_route_name] = upstream_id
                        logger.info(f"Created inline upstream: {upstream.name}")
                    except Exception as e:
                        error_msg = f"Failed to create inline upstream for route {route_config.get('name')}: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
            
            # Create routes with project prefix and link to service
            for route_config in config.get("routes", []):
                try:
                    # Add project prefix to route name and ID
                    original_name = route_config.get("name", "route")
                    route_config["name"] = f"{project_id}-{original_name}"
                    route_config["id"] = f"{project_id}-{original_name}"
                    
                    # Handle upstream inline or reference
                    if "upstream" in route_config:
                        # Replace inline upstream with upstream_id reference
                        if original_name in upstream_id_mapping:
                            route_config["upstream_id"] = upstream_id_mapping[original_name]
                            del route_config["upstream"]  # Remove inline upstream
                        # else: keep inline upstream as fallback
                    else:
                        # Link route to the project service
                        route_config["service_id"] = f"{project_id}-service"
                    
                    # Don't modify URI - keep it as defined in manifest
                    
                    # Add description metadata
                    route_config["desc"] = f"Route for {project_name} - {original_name}"
                    
                    # Handle plugins - they're already in dict format in our manifest
                    plugins_dict = route_config.get("plugins", {})
                    
                    # If plugins is a list, convert to dict
                    if isinstance(plugins_dict, list):
                        converted_plugins = {}
                        for plugin in plugins_dict:
                            if plugin.get("enabled", True):
                                plugin_config = plugin.get("config", {})
                                
                                # Update JWT plugin to use project consumer
                                if plugin["name"] == "jwt-auth":
                                    plugin_config["key"] = f"{project_id}-key"
                                
                                converted_plugins[plugin["name"]] = plugin_config
                        plugins_dict = converted_plugins
                    
                    route_config["plugins"] = plugins_dict
                    route = APISIXRoute(**route_config)
                    result = await self.create_route(route)
                    results["routes"].append(result)
                    logger.info(f"Created route: {route.name}")
                except Exception as e:
                    error_msg = f"Failed to create route {route_config.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
        # Set global plugins for this project (if needed)
        global_plugins = {}
        for apisix_module in apisix_modules:
            config = apisix_module.get("config", {})
            for plugin in config.get("global_plugins", []):
                if plugin.get("enabled", True):
                    global_plugins[plugin["name"]] = plugin.get("config", {})
        
        if global_plugins:
            try:
                # Use project-specific global rule ID
                global_rule_id = f"{project_id}-global-plugins"
                result = await self.set_global_rule(global_rule_id, global_plugins)
                results["global_rules"].append(result)
                logger.info(f"Configured global plugins for {project_id}")
            except Exception as e:
                error_msg = f"Failed to set global plugins: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    async def cleanup_project_resources(self, project_id: str) -> Dict[str, Any]:
        """Clean up all APISIX resources for a specific project"""
        results = {
            "deleted_routes": 0,
            "deleted_upstreams": 0,
            "deleted_services": 0,
            "deleted_consumers": 0,
            "errors": []
        }
        
        try:
            # Delete routes
            routes = await self.list_routes()
            for route in routes:
                route_value = route.get("value", {})
                if route_value.get("name", "").startswith(f"{project_id}-"):
                    route_id = route.get("key", "").split("/")[-1]
                    if await self.delete_route(route_id):
                        results["deleted_routes"] += 1
                        logger.info(f"Deleted route: {route_id}")
            
            # Delete upstreams
            upstreams = await self.list_upstreams()
            for upstream in upstreams:
                upstream_value = upstream.get("value", {})
                if upstream_value.get("name", "").startswith(f"{project_id}-"):
                    upstream_id = upstream.get("key", "").split("/")[-1]
                    if await self.delete_upstream(upstream_id):
                        results["deleted_upstreams"] += 1
                        logger.info(f"Deleted upstream: {upstream_id}")
            
            # Delete services
            services = await self.list_services()
            for service in services:
                service_value = service.get("value", {})
                if service_value.get("name", "").startswith(f"{project_id}-"):
                    service_id = service.get("key", "").split("/")[-1]
                    if await self.delete_service(service_id):
                        results["deleted_services"] += 1
                        logger.info(f"Deleted service: {service_id}")
            
            # Delete consumer
            consumer_username = f"{project_id}-consumer"
            try:
                if await self.delete_consumer(consumer_username):
                    results["deleted_consumers"] += 1
                    logger.info(f"Deleted consumer: {consumer_username}")
            except:
                pass  # Consumer might not exist
            
        except Exception as e:
            error_msg = f"Failed to cleanup project resources: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    async def list_project_resources(self, project_id: str) -> Dict[str, Any]:
        """List all APISIX resources for a specific project"""
        resources = {
            "routes": [],
            "upstreams": [],
            "services": [],
            "consumers": [],
            "summary": {}
        }
        
        try:
            # List routes
            all_routes = await self.list_routes()
            for route in all_routes:
                route_value = route.get("value", {})
                if route_value.get("name", "").startswith(f"{project_id}-"):
                    resources["routes"].append({
                        "name": route_value.get("name"),
                        "uri": route_value.get("uri"),
                        "methods": route_value.get("methods", []),
                        "service_id": route_value.get("service_id"),
                        "desc": route_value.get("desc", "")
                    })
            
            # List upstreams
            all_upstreams = await self.list_upstreams()
            for upstream in all_upstreams:
                upstream_value = upstream.get("value", {})
                if upstream_value.get("name", "").startswith(f"{project_id}-"):
                    resources["upstreams"].append({
                        "name": upstream_value.get("name"),
                        "type": upstream_value.get("type"),
                        "nodes": upstream_value.get("nodes", {})
                    })
            
            # List services
            all_services = await self.list_services()
            for service in all_services:
                service_value = service.get("value", {})
                if service_value.get("name", "").startswith(f"{project_id}-"):
                    resources["services"].append({
                        "name": service_value.get("name"),
                        "desc": service_value.get("desc", ""),
                        "upstream_id": service_value.get("upstream_id")
                    })
            
            # Check for consumer
            try:
                consumer = await self.get_consumer(f"{project_id}-consumer")
                resources["consumers"].append({
                    "username": consumer.get("value", {}).get("username"),
                    "desc": consumer.get("value", {}).get("desc", ""),
                    "plugins": list(consumer.get("value", {}).get("plugins", {}).keys())
                })
            except:
                pass  # Consumer might not exist
            
            resources["summary"] = {
                "project_id": project_id,
                "total_routes": len(resources["routes"]),
                "total_upstreams": len(resources["upstreams"]),
                "total_services": len(resources["services"]),
                "total_consumers": len(resources["consumers"])
            }
            
        except Exception as e:
            logger.error(f"Failed to list project resources: {str(e)}")
        
        return resources
    
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
