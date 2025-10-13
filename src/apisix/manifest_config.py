"""
APISIX Manifest Configuration
Handles configuration from Control Tower manifests
"""

import logging
from typing import Dict, Any
from .models import APISIXRoute, APISIXUpstream, APISIXService, APISIXConsumer

logger = logging.getLogger(__name__)


class ManifestConfigurator:
    """Configures APISIX from Control Tower manifests"""
    
    def __init__(self, route_manager, upstream_manager, service_manager, consumer_manager, global_rules_manager):
        self.route_manager = route_manager
        self.upstream_manager = upstream_manager
        self.service_manager = service_manager
        self.consumer_manager = consumer_manager
        self.global_rules_manager = global_rules_manager
    
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
        
        # Collect all unique consumers and services from APISIX modules
        consumer_configs = []
        service_configs = []
        seen_consumer_usernames = set()
        seen_service_ids = set()
        
        for apisix_module in apisix_modules:
            config = apisix_module.get("config", {})
            
            # Collect unique consumers
            if config.get("consumer"):
                consumer = config.get("consumer")
                username = consumer.get("username", "consumer")
                if username not in seen_consumer_usernames:
                    consumer_configs.append(consumer)
                    seen_consumer_usernames.add(username)
            
            # Collect unique services
            if config.get("service"):
                service = config.get("service")
                service_id = service.get("id", "service")
                if service_id not in seen_service_ids:
                    service_configs.append(service)
                    seen_service_ids.add(service_id)
        
        # Create all consumers
        for consumer_config in consumer_configs:
            try:
                # Add project_id prefix to username if not already present
                username = consumer_config.get("username", "consumer")
                if not username.startswith(f"{project_id}_"):
                    consumer_config["username"] = f"{project_id}_{username}"
                
                # APISIX consumer usernames must match pattern ^[a-zA-Z0-9_]+$
                # Replace hyphens with underscores to comply
                consumer_config["username"] = consumer_config["username"].replace("-", "_")
                
                consumer = APISIXConsumer(**consumer_config)
                result = await self.consumer_manager.create_consumer(consumer)
                results["consumers"].append(result)
                logger.info(f"Created consumer from manifest: {consumer.username}")
            except Exception as e:
                error_msg = f"Failed to create consumer {consumer_config.get('username')}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # Create all services
        for service_config in service_configs:
            try:
                # Add project_id prefix to service id and name if not already present
                service_id = service_config.get("id", "service")
                if not service_id.startswith(f"{project_id}-"):
                    service_config["id"] = f"{project_id}-{service_id}"
                
                service_name = service_config.get("name", "service")
                if not service_name.startswith(f"{project_id}-"):
                    service_config["name"] = f"{project_id}-{service_name}"
                
                service = APISIXService(**service_config)
                result = await self.service_manager.create_service(service)
                results["services"].append(result)
                logger.info(f"Created service from manifest: {service.name}")
            except Exception as e:
                error_msg = f"Failed to create service {service_config.get('id')}: {str(e)}"
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
                    result = await self.upstream_manager.create_upstream(upstream)
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
                        
                        result = await self.upstream_manager.create_upstream(upstream)
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
                    result = await self.route_manager.create_route(route)
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
                result = await self.global_rules_manager.set_global_rule(global_rule_id, global_plugins)
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
            routes = await self.route_manager.list_routes()
            for route in routes:
                route_value = route.get("value", {})
                if route_value.get("name", "").startswith(f"{project_id}-"):
                    route_id = route.get("key", "").split("/")[-1]
                    if await self.route_manager.delete_route(route_id):
                        results["deleted_routes"] += 1
                        logger.info(f"Deleted route: {route_id}")
            
            # Delete upstreams
            upstreams = await self.upstream_manager.list_upstreams()
            for upstream in upstreams:
                upstream_value = upstream.get("value", {})
                if upstream_value.get("name", "").startswith(f"{project_id}-"):
                    upstream_id = upstream.get("key", "").split("/")[-1]
                    if await self.upstream_manager.delete_upstream(upstream_id):
                        results["deleted_upstreams"] += 1
                        logger.info(f"Deleted upstream: {upstream_id}")
            
            # Delete services
            services = await self.service_manager.list_services()
            for service in services:
                service_value = service.get("value", {})
                if service_value.get("name", "").startswith(f"{project_id}-"):
                    service_id = service.get("key", "").split("/")[-1]
                    if await self.service_manager.delete_service(service_id):
                        results["deleted_services"] += 1
                        logger.info(f"Deleted service: {service_id}")
            
            # Delete consumer
            consumer_username = f"{project_id}-consumer"
            try:
                if await self.consumer_manager.delete_consumer(consumer_username):
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
            all_routes = await self.route_manager.list_routes()
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
            all_upstreams = await self.upstream_manager.list_upstreams()
            for upstream in all_upstreams:
                upstream_value = upstream.get("value", {})
                if upstream_value.get("name", "").startswith(f"{project_id}-"):
                    resources["upstreams"].append({
                        "name": upstream_value.get("name"),
                        "type": upstream_value.get("type"),
                        "nodes": upstream_value.get("nodes", {})
                    })
            
            # List services
            all_services = await self.service_manager.list_services()
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
                consumer = await self.consumer_manager.get_consumer(f"{project_id}-consumer")
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
