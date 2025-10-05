"""
APISIX Plugin Builders
Helper functions to build plugin configurations including Langfuse integration
"""

from typing import Dict, Any, Optional, List


class PluginBuilder:
    """Builder class for APISIX plugin configurations"""
    
    @staticmethod
    def build_jwt_plugin(
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
    
    @staticmethod
    def build_rate_limit_plugin(
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
    
    @staticmethod
    def build_cors_plugin(
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
    
    @staticmethod
    def build_prometheus_plugin() -> Dict[str, Any]:
        """Build Prometheus metrics plugin configuration"""
        return {
            "prometheus": {
                "prefer_name": True
            }
        }
    
    @staticmethod
    def build_logger_plugin(
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
    
    @staticmethod
    def build_langfuse_plugin(
        public_key: str,
        secret_key: str,
        host: str = "https://cloud.langfuse.com",
        enabled: bool = True,
        sample_rate: float = 1.0,
        batch_max_size: int = 100,
        flush_interval: int = 3,
        include_request_body: bool = True,
        include_response_body: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Langfuse observability plugin configuration for LLM tracing
        
        Args:
            public_key: Langfuse public API key
            secret_key: Langfuse secret API key
            host: Langfuse host URL (default: cloud.langfuse.com)
            enabled: Enable/disable the plugin
            sample_rate: Sampling rate (0.0 to 1.0)
            batch_max_size: Maximum batch size before flushing
            flush_interval: Flush interval in seconds
            include_request_body: Include request body in traces
            include_response_body: Include response body in traces
            metadata: Additional metadata to include in traces
        
        Returns:
            Plugin configuration dict
        
        Note: This uses APISIX's http-logger plugin to send traces to Langfuse.
        For full Langfuse integration, you may need a custom plugin or use
        serverless-post-function to format data for Langfuse API.
        """
        config = {
            "public_key": public_key,
            "secret_key": secret_key,
            "host": host,
            "sample_rate": sample_rate,
            "batch_max_size": batch_max_size,
            "flush_interval": flush_interval,
            "include_request_body": include_request_body,
            "include_response_body": include_response_body
        }
        
        if metadata:
            config["metadata"] = metadata
        
        # Use http-logger to send to Langfuse ingestion endpoint
        return {
            "http-logger": {
                "uri": f"{host}/api/public/ingestion",
                "auth_header": f"Basic {public_key}:{secret_key}",
                "batch_max_size": batch_max_size,
                "inactive_timeout": flush_interval,
                "buffer_duration": flush_interval,
                "max_retry_count": 3,
                "retry_delay": 1,
                "include_req_body": include_request_body,
                "include_resp_body": include_response_body,
                "concat_method": "json"
            }
        }
    
    @staticmethod
    def build_langfuse_serverless_plugin(
        public_key: str,
        secret_key: str,
        host: str = "https://cloud.langfuse.com",
        project_name: Optional[str] = None,
        trace_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Langfuse plugin using serverless-post-function for custom formatting
        
        This approach uses APISIX's serverless plugin to format and send data
        directly to Langfuse API in the correct format.
        
        Args:
            public_key: Langfuse public API key
            secret_key: Langfuse secret API key
            host: Langfuse host URL
            project_name: Optional project name for grouping traces
            trace_metadata: Additional metadata for traces
        
        Returns:
            Serverless plugin configuration
        """
        lua_code = f"""
local http = require("resty.http")
local cjson = require("cjson")
local ngx = ngx

return function(conf, ctx)
    local httpc = http.new()
    
    -- Extract request/response data
    local trace_data = {{
        name = ctx.var.uri,
        userId = ctx.var.remote_user or "anonymous",
        metadata = {cjson.encode(trace_metadata or {})},
        tags = {{"{project_name or 'apisix'}"}},
        timestamp = ngx.now() * 1000,
        input = {{
            method = ctx.var.request_method,
            uri = ctx.var.uri,
            headers = ngx.req.get_headers(),
        }},
        output = {{
            status = ngx.status,
            latency = ctx.var.request_time * 1000
        }}
    }}
    
    -- Send to Langfuse
    local res, err = httpc:request_uri("{host}/api/public/traces", {{
        method = "POST",
        body = cjson.encode(trace_data),
        headers = {{
            ["Content-Type"] = "application/json",
            ["Authorization"] = "Basic " .. ngx.encode_base64("{public_key}:{secret_key}")
        }}
    }})
    
    if not res then
        ngx.log(ngx.ERR, "Failed to send trace to Langfuse: ", err)
    end
end
"""
        
        return {
            "serverless-post-function": {
                "phase": "log",
                "functions": [lua_code]
            }
        }
    
    @staticmethod
    def build_opentelemetry_plugin(
        endpoint: str,
        service_name: str = "apisix-gateway",
        batch_span_processor: Optional[Dict[str, Any]] = None,
        resource: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Build OpenTelemetry plugin for distributed tracing
        
        Can be used with Langfuse's OpenTelemetry integration
        
        Args:
            endpoint: OTLP endpoint (e.g., http://langfuse:4318/v1/traces)
            service_name: Service name for traces
            batch_span_processor: Batch processor configuration
            resource: Resource attributes
        
        Returns:
            OpenTelemetry plugin configuration
        """
        config = {
            "resource": resource or {
                "service.name": service_name,
                "service.version": "1.0.0"
            },
            "collector": {
                "address": endpoint,
                "request_timeout": 3,
                "request_headers": {
                    "Content-Type": "application/json"
                }
            },
            "batch_span_processor": batch_span_processor or {
                "drop_on_queue_full": False,
                "max_queue_size": 2048,
                "batch_timeout": 5,
                "max_export_batch_size": 256,
                "inactive_timeout": 2
            }
        }
        
        return {
            "opentelemetry": config
        }
    
    @staticmethod
    def build_request_id_plugin(
        header_name: str = "X-Request-Id",
        algorithm: str = "uuid"
    ) -> Dict[str, Any]:
        """
        Build request ID plugin for trace correlation
        
        Args:
            header_name: Header name for request ID
            algorithm: Algorithm to generate ID (uuid, snowflake, nanoid)
        
        Returns:
            Request ID plugin configuration
        """
        return {
            "request-id": {
                "header_name": header_name,
                "include_in_response": True,
                "algorithm": algorithm
            }
        }
    
    @staticmethod
    def build_combined_observability_plugins(
        langfuse_public_key: str,
        langfuse_secret_key: str,
        langfuse_host: str = "https://cloud.langfuse.com",
        prometheus_enabled: bool = True,
        request_id_enabled: bool = True,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a combined set of observability plugins including Langfuse
        
        Args:
            langfuse_public_key: Langfuse public key
            langfuse_secret_key: Langfuse secret key
            langfuse_host: Langfuse host URL
            prometheus_enabled: Enable Prometheus metrics
            request_id_enabled: Enable request ID tracking
            project_name: Project name for Langfuse
        
        Returns:
            Combined plugin configuration dict
        """
        plugins = {}
        
        # Add request ID for trace correlation
        if request_id_enabled:
            plugins.update(PluginBuilder.build_request_id_plugin())
        
        # Add Prometheus metrics
        if prometheus_enabled:
            plugins.update(PluginBuilder.build_prometheus_plugin())
        
        # Add Langfuse tracing
        plugins.update(
            PluginBuilder.build_langfuse_plugin(
                public_key=langfuse_public_key,
                secret_key=langfuse_secret_key,
                host=langfuse_host,
                metadata={"project": project_name} if project_name else None
            )
        )
        
        return plugins
