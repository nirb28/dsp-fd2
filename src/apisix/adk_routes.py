"""
ADK Route Generation for APISIX.

Generates APISIX routes for ADK modules defined in Control Tower manifests.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ADKRouteGenerator:
    """
    Generates APISIX routes for ADK modules.
    
    Creates routes for:
    - Agent execution and streaming
    - Tool execution and schema retrieval
    - Graph execution and streaming
    - Capability status and management
    """
    
    def __init__(
        self,
        project_id: str,
        apisix_client: Any = None,
        default_plugins: Optional[List[Dict[str, Any]]] = None
    ):
        self.project_id = project_id
        self.apisix_client = apisix_client
        self.default_plugins = default_plugins or []
    
    def generate_agent_routes(
        self,
        module_name: str,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate APISIX routes for an ADK agent module.
        
        Creates routes for:
        - POST /{project_id}/agents/{module_name}/run - Execute agent
        - POST /{project_id}/agents/{module_name}/stream - Stream execution
        - GET /{project_id}/agents/{module_name}/info - Get agent info
        """
        service_url = config.get("service_url", "http://localhost:8100")
        agent_id = config.get("agent_id", module_name)
        timeout = config.get("request_timeout", 120)
        
        # Build upstream
        upstream = {
            "type": "roundrobin",
            "nodes": {service_url.replace("http://", "").replace("https://", ""): 1},
            "timeout": {
                "connect": 30,
                "send": timeout,
                "read": timeout
            }
        }
        
        # Build plugins
        plugins = self._build_agent_plugins(config)
        
        routes = [
            {
                "name": f"{self.project_id}-agent-{module_name}-run",
                "uri": f"/{self.project_id}/agents/{module_name}/run",
                "methods": ["POST"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Execute ADK agent: {module_name}",
                "_adk_module": {
                    "type": "adk_agent",
                    "name": module_name,
                    "agent_id": agent_id
                }
            },
            {
                "name": f"{self.project_id}-agent-{module_name}-stream",
                "uri": f"/{self.project_id}/agents/{module_name}/stream",
                "methods": ["POST"],
                "upstream": upstream,
                "plugins": {
                    **plugins,
                    "response-rewrite": {
                        "headers": {
                            "Content-Type": "text/event-stream",
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive"
                        }
                    }
                },
                "vars": [],
                "desc": f"Stream ADK agent: {module_name}"
            },
            {
                "name": f"{self.project_id}-agent-{module_name}-info",
                "uri": f"/{self.project_id}/agents/{module_name}/info",
                "methods": ["GET"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Get ADK agent info: {module_name}"
            }
        ]
        
        return routes
    
    def generate_tool_routes(
        self,
        module_name: str,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate APISIX routes for an ADK tool module.
        
        Creates routes for:
        - POST /{project_id}/tools/{module_name}/execute - Execute tool
        - GET /{project_id}/tools/{module_name}/schema - Get tool schema
        """
        service_url = config.get("service_url", "http://localhost:8100")
        tool_id = config.get("tool_id", module_name)
        timeout = config.get("timeout", 30)
        
        upstream = {
            "type": "roundrobin",
            "nodes": {service_url.replace("http://", "").replace("https://", ""): 1},
            "timeout": {
                "connect": 10,
                "send": timeout,
                "read": timeout
            }
        }
        
        plugins = self._build_tool_plugins(config)
        
        routes = [
            {
                "name": f"{self.project_id}-tool-{module_name}-execute",
                "uri": f"/{self.project_id}/tools/{module_name}/execute",
                "methods": ["POST"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Execute ADK tool: {module_name}",
                "_adk_module": {
                    "type": "adk_tool",
                    "name": module_name,
                    "tool_id": tool_id
                }
            },
            {
                "name": f"{self.project_id}-tool-{module_name}-schema",
                "uri": f"/{self.project_id}/tools/{module_name}/schema",
                "methods": ["GET"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Get ADK tool schema: {module_name}"
            }
        ]
        
        return routes
    
    def generate_graph_routes(
        self,
        module_name: str,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate APISIX routes for an ADK graph module.
        
        Creates routes for:
        - POST /{project_id}/graphs/{module_name}/run - Execute graph
        - POST /{project_id}/graphs/{module_name}/stream - Stream execution
        - GET /{project_id}/graphs/{module_name}/info - Get graph info
        - GET /{project_id}/graphs/{module_name}/state - Get graph state
        """
        service_url = config.get("service_url", "http://localhost:8100")
        graph_id = config.get("graph_id", module_name)
        timeout = config.get("timeout_seconds", 300)
        
        upstream = {
            "type": "roundrobin",
            "nodes": {service_url.replace("http://", "").replace("https://", ""): 1},
            "timeout": {
                "connect": 30,
                "send": timeout,
                "read": timeout
            }
        }
        
        plugins = self._build_graph_plugins(config)
        
        routes = [
            {
                "name": f"{self.project_id}-graph-{module_name}-run",
                "uri": f"/{self.project_id}/graphs/{module_name}/run",
                "methods": ["POST"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Execute ADK graph: {module_name}",
                "_adk_module": {
                    "type": "adk_graph",
                    "name": module_name,
                    "graph_id": graph_id
                }
            },
            {
                "name": f"{self.project_id}-graph-{module_name}-stream",
                "uri": f"/{self.project_id}/graphs/{module_name}/stream",
                "methods": ["POST"],
                "upstream": upstream,
                "plugins": {
                    **plugins,
                    "response-rewrite": {
                        "headers": {
                            "Content-Type": "text/event-stream",
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive"
                        }
                    }
                },
                "vars": [],
                "desc": f"Stream ADK graph: {module_name}"
            },
            {
                "name": f"{self.project_id}-graph-{module_name}-info",
                "uri": f"/{self.project_id}/graphs/{module_name}/info",
                "methods": ["GET"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Get ADK graph info: {module_name}"
            },
            {
                "name": f"{self.project_id}-graph-{module_name}-state",
                "uri": f"/{self.project_id}/graphs/{module_name}/state",
                "methods": ["GET"],
                "upstream": upstream,
                "plugins": plugins,
                "vars": [],
                "desc": f"Get ADK graph state: {module_name}"
            }
        ]
        
        return routes
    
    def _build_agent_plugins(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build APISIX plugins for agent routes."""
        plugins = {}
        
        # JWT authentication
        if config.get("jwt_module_reference"):
            plugins["jwt-auth"] = {}
        
        # Rate limiting
        if config.get("rate_limit_enabled"):
            plugins["limit-req"] = {
                "rate": config.get("requests_per_minute", 60) / 60,
                "burst": 10,
                "key": "remote_addr"
            }
        
        # Logging
        plugins["prometheus"] = {}
        plugins["http-logger"] = {
            "uri": "http://localhost:9080/apisix/admin/logs"
        }
        
        return plugins
    
    def _build_tool_plugins(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build APISIX plugins for tool routes."""
        plugins = {}
        
        if config.get("jwt_module_reference"):
            plugins["jwt-auth"] = {}
        
        plugins["prometheus"] = {}
        
        return plugins
    
    def _build_graph_plugins(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build APISIX plugins for graph routes."""
        plugins = {}
        
        if config.get("jwt_module_reference"):
            plugins["jwt-auth"] = {}
        
        plugins["prometheus"] = {}
        
        return plugins
    
    def generate_all_routes_from_manifest(
        self,
        manifest_modules: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate all ADK routes from manifest modules.
        
        Args:
            manifest_modules: List of module configurations from manifest
            
        Returns:
            Dict with routes organized by type (agents, tools, graphs)
        """
        all_routes = {
            "agents": [],
            "tools": [],
            "graphs": []
        }
        
        for module in manifest_modules:
            module_type = module.get("module_type")
            module_name = module.get("name")
            config = module.get("config", {})
            
            if module.get("status") != "enabled":
                logger.info(f"Skipping disabled module: {module_name}")
                continue
            
            if module_type == "adk_agent":
                routes = self.generate_agent_routes(module_name, config)
                all_routes["agents"].extend(routes)
                logger.info(f"Generated {len(routes)} routes for agent: {module_name}")
                
            elif module_type == "adk_tool":
                routes = self.generate_tool_routes(module_name, config)
                all_routes["tools"].extend(routes)
                logger.info(f"Generated {len(routes)} routes for tool: {module_name}")
                
            elif module_type == "adk_graph":
                routes = self.generate_graph_routes(module_name, config)
                all_routes["graphs"].extend(routes)
                logger.info(f"Generated {len(routes)} routes for graph: {module_name}")
        
        return all_routes
    
    async def deploy_routes(
        self,
        routes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Deploy routes to APISIX.
        
        Args:
            routes: List of route configurations
            
        Returns:
            Deployment results
        """
        if not self.apisix_client:
            return {"success": False, "error": "APISIX client not configured"}
        
        results = {
            "success": True,
            "deployed": [],
            "failed": []
        }
        
        for route in routes:
            try:
                route_name = route.get("name")
                # Create or update route in APISIX
                await self.apisix_client.create_route(route)
                results["deployed"].append(route_name)
                logger.info(f"Deployed route: {route_name}")
            except Exception as e:
                results["failed"].append({
                    "route": route.get("name"),
                    "error": str(e)
                })
                logger.error(f"Failed to deploy route {route.get('name')}: {e}")
        
        if results["failed"]:
            results["success"] = False
        
        return results
    
    def get_route_summary(self, routes: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Get a summary of generated routes."""
        return {
            "project_id": self.project_id,
            "total_routes": sum(len(r) for r in routes.values()),
            "agent_routes": len(routes.get("agents", [])),
            "tool_routes": len(routes.get("tools", [])),
            "graph_routes": len(routes.get("graphs", [])),
            "endpoints": self._list_endpoints(routes)
        }
    
    def _list_endpoints(self, routes: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """List all endpoints from routes."""
        endpoints = []
        for route_list in routes.values():
            for route in route_list:
                method = route.get("methods", ["GET"])[0]
                uri = route.get("uri", "")
                endpoints.append(f"{method} {uri}")
        return sorted(endpoints)


def generate_adk_routes_for_project(
    project_id: str,
    manifest_modules: List[Dict[str, Any]],
    apisix_client: Any = None
) -> Dict[str, Any]:
    """
    Convenience function to generate ADK routes for a project.
    
    Args:
        project_id: Project identifier
        manifest_modules: Modules from Control Tower manifest
        apisix_client: Optional APISIX client for deployment
        
    Returns:
        Route generation results including summary
    """
    generator = ADKRouteGenerator(project_id, apisix_client)
    routes = generator.generate_all_routes_from_manifest(manifest_modules)
    summary = generator.get_route_summary(routes)
    
    return {
        "routes": routes,
        "summary": summary
    }
