"""
Manifest Help Service
Extracts and formats manifest information for help endpoints
Safely redacts secrets and sensitive information
"""

import re
from typing import Dict, Any, List, Optional


class ManifestHelpService:
    """Service to extract and format manifest information for help endpoints"""
    
    # Patterns to identify secret fields
    SECRET_PATTERNS = [
        r'.*secret.*',
        r'.*password.*',
        r'.*token.*',
        r'.*key.*',
        r'.*api_key.*',
        r'.*auth.*',
        r'.*credential.*',
    ]
    
    # Fields that should be redacted
    SECRET_FIELDS = {
        'secret', 'password', 'token', 'api_key', 'secret_key', 
        'jwt_secret_key', 'jwe_encryption_key', 'groq_api_key',
        'langfuse_secret_key', 'vault_token', 'role_id', 'secret_id',
        'encryption_key', 'public_key', 'private_key'
    }
    
    @staticmethod
    def is_secret_field(field_name: str) -> bool:
        """Check if a field name indicates it contains secret data"""
        field_lower = field_name.lower()
        
        # Check exact matches
        if field_lower in ManifestHelpService.SECRET_FIELDS:
            return True
        
        # Check patterns
        for pattern in ManifestHelpService.SECRET_PATTERNS:
            if re.match(pattern, field_lower, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def redact_secrets(data: Any, parent_key: str = "") -> Any:
        """Recursively redact secrets from data structure"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                full_key = f"{parent_key}.{key}" if parent_key else key
                
                # Check if this field should be redacted
                if ManifestHelpService.is_secret_field(key):
                    # Show type hint instead of value
                    if isinstance(value, str):
                        if value.startswith("${") or value.startswith("env:") or value.startswith("config:"):
                            result[key] = f"<reference: {value[:20]}...>"
                        else:
                            result[key] = "<redacted>"
                    else:
                        result[key] = "<redacted>"
                else:
                    result[key] = ManifestHelpService.redact_secrets(value, full_key)
            return result
        elif isinstance(data, list):
            return [ManifestHelpService.redact_secrets(item, parent_key) for item in data]
        else:
            return data
    
    @staticmethod
    def extract_endpoints(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all endpoints from manifest modules"""
        endpoints = []
        modules = manifest.get("modules", [])
        
        for module in modules:
            module_type = module.get("module_type")
            module_name = module.get("name")
            config = module.get("config", {})
            
            # Extract inference endpoints
            if module_type == "inference_endpoint":
                endpoint_url = config.get("endpoint_url", "")
                # Get description, fallback to system_prompt (truncated), or empty string
                description = config.get("description")
                if not description:
                    system_prompt = config.get("system_prompt") or ""
                    description = system_prompt[:100] if system_prompt else ""
                
                endpoints.append({
                    "type": "inference",
                    "module_name": module_name,
                    "url": endpoint_url,
                    "method": "POST",
                    "model": config.get("model_name"),
                    "description": description,
                    "parameters": {
                        "max_tokens": config.get("max_tokens"),
                        "temperature": config.get("temperature"),
                    },
                    "dependencies": module.get("dependencies", [])
                })
            
            # Extract API gateway routes
            elif module_type == "api_gateway":
                routes = config.get("routes", [])
                for route in routes:
                    route_info = {
                        "type": "api_gateway",
                        "module_name": module_name,
                        "route_name": route.get("name"),
                        "uri": route.get("uri"),
                        "methods": route.get("methods", []),
                        "plugins": list(route.get("plugins", {}).keys()),
                        "upstream": ManifestHelpService.redact_secrets(route.get("upstream", {})),
                        "dependencies": module.get("dependencies", [])
                    }
                    endpoints.append(route_info)
            
            # Extract health check endpoints
            elif module_type == "health_check":
                endpoints.append({
                    "type": "health_check",
                    "module_name": module_name,
                    "paths": {
                        "main": config.get("endpoint_path", "/health"),
                        "liveness": config.get("liveness_path", "/health/live"),
                        "readiness": config.get("readiness_path", "/health/ready"),
                    },
                    "method": "GET",
                    "check_interval": config.get("check_interval_seconds"),
                    "targets": len(config.get("targets", []))
                })
            
            # Extract metrics endpoints
            elif module_type == "metrics":
                endpoints.append({
                    "type": "metrics",
                    "module_name": module_name,
                    "path": config.get("endpoint_path", "/metrics"),
                    "method": "GET",
                    "namespace": config.get("namespace"),
                    "metrics": config.get("default_metrics", [])
                })
        
        return endpoints
    
    @staticmethod
    def extract_authentication(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract authentication configuration"""
        auth_configs = []
        modules = manifest.get("modules", [])
        
        for module in modules:
            module_type = module.get("module_type")
            module_name = module.get("name")
            config = module.get("config", {})
            
            if module_type == "jwt_config":
                jwe_config = config.get("jwe_config") or {}
                auth_info = {
                    "module_name": module_name,
                    "type": "jwt",
                    "service_url": config.get("service_url", ""),
                    "claims": ManifestHelpService.redact_secrets(config.get("claims") or {}),
                    "jwe_enabled": jwe_config.get("enabled", False),
                }
                
                if auth_info["jwe_enabled"]:
                    auth_info["jwe_algorithm"] = jwe_config.get("algorithm")
                    auth_info["jwe_encryption"] = jwe_config.get("encryption")
                
                auth_configs.append(auth_info)
            
            elif module_type == "api_gateway":
                consumer = config.get("consumer") or {}
                if consumer:
                    plugins = consumer.get("plugins") or {}
                    auth_info = {
                        "module_name": module_name,
                        "type": "api_gateway_consumer",
                        "username": consumer.get("username"),
                        "auth_plugins": list(plugins.keys()),
                        "description": consumer.get("desc", "")
                    }
                    auth_configs.append(auth_info)
        
        return auth_configs
    
    @staticmethod
    def extract_security_features(manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security features from manifest"""
        security = {
            "authentication": [],
            "rate_limiting": [],
            "encryption": [],
            "monitoring": []
        }
        
        modules = manifest.get("modules", [])
        
        for module in modules:
            module_type = module.get("module_type")
            module_name = module.get("name")
            config = module.get("config", {})
            
            # JWT authentication
            if module_type == "jwt_config":
                jwe_config = config.get("jwe_config") or {}
                security["authentication"].append({
                    "module": module_name,
                    "type": "JWT",
                    "jwe_encrypted": jwe_config.get("enabled", False)
                })
            
            # API Gateway plugins
            if module_type == "api_gateway":
                routes = config.get("routes", [])
                for route in routes:
                    plugins = route.get("plugins", {})
                    
                    # Check for auth plugins
                    if "jwt-auth" in plugins:
                        security["authentication"].append({
                            "route": route.get("uri"),
                            "type": "JWT Auth Plugin"
                        })
                    
                    if "jwe-decrypt" in plugins:
                        security["encryption"].append({
                            "route": route.get("uri"),
                            "type": "JWE Decryption"
                        })
                    
                    # Rate limiting
                    if any(k in plugins for k in ["limit-req", "limit-count", "limit-conn"]):
                        security["rate_limiting"].append({
                            "route": route.get("uri"),
                            "plugins": [k for k in plugins.keys() if "limit" in k]
                        })
            
            # Monitoring
            if module_type == "monitoring":
                security["monitoring"].append({
                    "module": module_name,
                    "provider": config.get("provider"),
                    "project": config.get("project_name")
                })
            
            # Vault
            if module_type == "vault":
                security["encryption"].append({
                    "module": module_name,
                    "type": "HashiCorp Vault",
                    "instances": len(config.get("vault_instances", []))
                })
        
        return security
    
    @staticmethod
    def _generate_inference_examples(manifest: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        """Generate usage examples for inference endpoints"""
        examples = []
        modules = manifest.get("modules", [])
        
        for module in modules:
            if module.get("module_type") == "inference_endpoint":
                module_name = module.get("name")
                config = module.get("config", {})
                
                # Extract the URI from endpoint_url or construct it
                endpoint_url = config.get("endpoint_url", "")
                
                # Try to extract just the path from the full URL
                if endpoint_url:
                    # If it's a full URL, extract the path
                    if "://" in endpoint_url:
                        from urllib.parse import urlparse
                        parsed = urlparse(endpoint_url)
                        uri = parsed.path
                    else:
                        uri = endpoint_url
                else:
                    uri = f"/{project_id}/{module_name}"
                
                example = {
                    "endpoint_name": module_name,
                    "uri": uri,
                    "method": "POST",
                    "description": config.get("description", "")[:100] if config.get("description") else "",
                    "example_request": {
                        "headers": {
                            "Authorization": "Bearer <your-jwt-token>",
                            "Content-Type": "application/json"
                        },
                        "body": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Your prompt here"
                                }
                            ]
                        }
                    }
                }
                
                # Add optional parameters if they exist
                if config.get("max_tokens"):
                    example["example_request"]["body"]["max_tokens"] = config.get("max_tokens")
                if config.get("temperature"):
                    example["example_request"]["body"]["temperature"] = config.get("temperature")
                
                examples.append(example)
        
        return examples
    
    @staticmethod
    def extract_module_summary(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract summary of all modules"""
        modules = manifest.get("modules", [])
        summary = []
        
        for module in modules:
            summary.append({
                "name": module.get("name"),
                "type": module.get("module_type"),
                "version": module.get("version", "N/A"),
                "status": module.get("status", "enabled"),
                "description": module.get("description", ""),
                "dependencies": module.get("dependencies", [])
            })
        
        return summary
    
    @staticmethod
    def generate_help(manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive help information from manifest"""
        if not manifest:
            raise ValueError("Manifest cannot be None or empty")
        
        project_id = manifest.get("project_id", "unknown")
        project_name = manifest.get("project_name", "Unknown Project")
        environment = manifest.get("environment", "production")
        
        help_info = {
            "project": {
                "id": project_id,
                "name": project_name,
                "owner": manifest.get("owner", "Unknown"),
                "environment": environment
            },
            "endpoints": ManifestHelpService.extract_endpoints(manifest),
            "authentication": ManifestHelpService.extract_authentication(manifest),
            "security": ManifestHelpService.extract_security_features(manifest),
            "modules": ManifestHelpService.extract_module_summary(manifest),
            "usage": {
                "token_endpoint": f"/{project_id}/{{jwt_module_name}}/token",
                "token_example": {
                    "url": f"/{project_id}/auth/token",
                    "method": "POST",
                    "body": {
                        "username": "your-username",
                        "password": "your-password"
                    }
                },
                "authenticated_request_example": {
                    "headers": {
                        "Authorization": "Bearer <your-jwt-token>",
                        "Content-Type": "application/json"
                    }
                },
                "inference_endpoint_examples": ManifestHelpService._generate_inference_examples(manifest, project_id)
            },
            "summary": {
                "total_modules": len(manifest.get("modules", [])),
                "total_endpoints": len(ManifestHelpService.extract_endpoints(manifest)),
                "environments_configured": list(manifest.get("environments", {}).keys())
            }
        }
        
        return help_info
