# APISIX Langfuse Integration Guide

## Overview

The DSP Front Door (FD2) APISIX client has been refactored into a modular architecture with built-in support for **Langfuse observability** for LLM tracing and monitoring.

## New Modular Structure

The APISIX client is now organized into specialized modules:

```
src/apisix/
├── __init__.py              # Package exports
├── client.py                # Main client (composition pattern)
├── models.py                # Pydantic data models
├── plugins.py               # Plugin builders (including Langfuse)
├── routes.py                # Route management
├── upstreams.py             # Upstream management
├── services.py              # Service management
├── consumers.py             # Consumer management
├── global_rules.py          # Global rules management
└── manifest_config.py       # Manifest configuration
```

## Usage

### Basic Import

```python
from apisix import APISIXClient

# Initialize client
client = APISIXClient(
    admin_url="http://localhost:9180",
    admin_key="your-admin-key"
)
```

### Using Plugin Builders

```python
# Access plugin builder
plugins = client.plugins

# Or import directly
from apisix.plugins import PluginBuilder
```

## Langfuse Integration

### What is Langfuse?

Langfuse is an open-source LLM engineering platform that provides:
- **Tracing**: Track LLM calls, prompts, and completions
- **Monitoring**: Observe latency, costs, and quality metrics
- **Analytics**: Analyze usage patterns and model performance
- **Debugging**: Inspect individual traces and identify issues

### Configuration Options

#### 1. Basic Langfuse Plugin

```python
from apisix import APISIXClient

client = APISIXClient(admin_url="http://localhost:9180", admin_key="admin-key")

# Build Langfuse plugin
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",  # or self-hosted URL
    sample_rate=1.0,  # 100% sampling
    batch_max_size=100,
    flush_interval=3,
    include_request_body=True,
    include_response_body=True,
    metadata={"environment": "production", "service": "llm-gateway"}
)
```

#### 2. Combined Observability Stack

```python
# Langfuse + Prometheus + Request ID tracking
observability_plugins = client.build_combined_observability_plugins(
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
    langfuse_host="https://cloud.langfuse.com",
    prometheus_enabled=True,
    request_id_enabled=True,
    project_name="my-llm-project"
)
```

#### 3. OpenTelemetry Integration

For advanced tracing with Langfuse's OpenTelemetry support:

```python
otel_plugin = client.plugins.build_opentelemetry_plugin(
    endpoint="http://langfuse:4318/v1/traces",
    service_name="apisix-llm-gateway",
    resource={
        "service.name": "apisix-gateway",
        "service.version": "1.0.0",
        "deployment.environment": "production"
    }
)
```

### Adding Langfuse to Routes

#### Method 1: Per-Route Configuration

```python
from apisix.models import APISIXRoute

# Create route with Langfuse plugin
route = APISIXRoute(
    id="llm-inference-route",
    name="LLM Inference",
    uri="/v1/chat/completions",
    methods=["POST"],
    upstream_id="llm-upstream",
    plugins={
        **client.build_langfuse_plugin(
            public_key="pk-lf-...",
            secret_key="sk-lf-...",
            metadata={"route": "chat-completions"}
        ),
        **client.build_jwt_plugin(key="auth-key", secret="secret"),
        **client.build_rate_limit_plugin(rate=100, burst=200)
    }
)

await client.create_route(route)
```

#### Method 2: Global Plugin Rule

```python
# Apply Langfuse globally to all routes
global_plugins = client.build_combined_observability_plugins(
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
    project_name="global-llm-monitoring"
)

await client.set_global_rule("langfuse-global", global_plugins)
```

### Control Tower Manifest Integration

Add Langfuse configuration to your Control Tower manifest:

```json
{
  "project_id": "llm-project",
  "project_name": "LLM Service",
  "modules": [
    {
      "name": "apisix-gateway",
      "module_type": "api_gateway",
      "config": {
        "global_plugins": [
          {
            "name": "http-logger",
            "enabled": true,
            "config": {
              "uri": "https://cloud.langfuse.com/api/public/ingestion",
              "auth_header": "Basic ${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}",
              "batch_max_size": 100,
              "include_req_body": true,
              "include_resp_body": true
            }
          },
          {
            "name": "prometheus",
            "enabled": true,
            "config": {
              "prefer_name": true
            }
          },
          {
            "name": "request-id",
            "enabled": true,
            "config": {
              "header_name": "X-Request-Id",
              "include_in_response": true
            }
          }
        ],
        "routes": [
          {
            "name": "llm-chat",
            "uri": "/v1/chat/completions",
            "methods": ["POST"],
            "upstream": {
              "type": "roundrobin",
              "nodes": {
                "llm-service:8000": 1
              }
            },
            "plugins": {
              "jwt-auth": {
                "key": "auth-key",
                "secret": "${JWT_SECRET}"
              }
            }
          }
        ]
      }
    }
  ]
}
```

## Advanced Features

### Custom Langfuse Metadata

Add custom metadata to traces for better filtering and analysis:

```python
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    metadata={
        "environment": "production",
        "region": "us-east-1",
        "model_provider": "openai",
        "cost_center": "ai-research",
        "team": "ml-platform"
    }
)
```

### Sampling Configuration

Control trace sampling to reduce costs:

```python
# Sample 10% of requests
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    sample_rate=0.1  # 10% sampling
)
```

### Request ID Correlation

Enable request ID tracking for trace correlation:

```python
# Add request ID plugin
request_id_plugin = client.plugins.build_request_id_plugin(
    header_name="X-Request-Id",
    algorithm="uuid"
)

# Combine with Langfuse
route_plugins = {
    **request_id_plugin,
    **langfuse_plugin
}
```

## Monitoring Dashboard

### Langfuse Cloud

1. Sign up at [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a new project
3. Copy your public and secret keys
4. Configure APISIX plugins with your keys
5. View traces in the Langfuse dashboard

### Self-Hosted Langfuse

Deploy Langfuse locally:

```yaml
# docker-compose.yml
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/langfuse
      - NEXTAUTH_SECRET=your-secret
      - NEXTAUTH_URL=http://localhost:3000
```

Configure APISIX to use self-hosted instance:

```python
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://langfuse:3000"  # Self-hosted URL
)
```

## Best Practices

### 1. Environment-Specific Configuration

```python
import os

langfuse_config = {
    "public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
    "secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
    "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    "metadata": {
        "environment": os.getenv("ENVIRONMENT", "development")
    }
}

langfuse_plugin = client.build_langfuse_plugin(**langfuse_config)
```

### 2. Batching for Performance

```python
# Optimize for high-throughput scenarios
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    batch_max_size=500,  # Larger batches
    flush_interval=10,    # Longer intervals
    include_response_body=False  # Reduce payload size
)
```

### 3. Error Handling

The Langfuse plugin is designed to fail gracefully - if Langfuse is unavailable, requests will still be processed:

```python
# Langfuse errors won't block requests
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    # Plugin will log errors but continue serving traffic
)
```

### 4. Cost Optimization

```python
# Production: Full tracing
prod_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    sample_rate=1.0,
    include_request_body=True,
    include_response_body=True
)

# Development: Sampled tracing
dev_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    sample_rate=0.1,  # 10% sampling
    include_response_body=False  # Reduce data
)
```

## Example: Complete Setup

```python
import asyncio
from apisix import APISIXClient
from apisix.models import APISIXRoute, APISIXUpstream

async def setup_llm_gateway():
    # Initialize client
    client = APISIXClient(
        admin_url="http://localhost:9180",
        admin_key="admin-key"
    )
    
    try:
        # Create upstream
        upstream = APISIXUpstream(
            id="llm-upstream",
            name="LLM Service",
            type="roundrobin",
            nodes={"llm-service:8000": 1},
            timeout={"connect": 30, "send": 300, "read": 300}
        )
        await client.create_upstream(upstream)
        
        # Build observability plugins
        plugins = client.build_combined_observability_plugins(
            langfuse_public_key="pk-lf-...",
            langfuse_secret_key="sk-lf-...",
            prometheus_enabled=True,
            request_id_enabled=True,
            project_name="llm-gateway"
        )
        
        # Add authentication
        plugins.update(client.build_jwt_plugin(
            key="auth-key",
            secret="your-secret"
        ))
        
        # Add rate limiting
        plugins.update(client.build_rate_limit_plugin(
            rate=100,
            burst=200,
            key="remote_addr"
        ))
        
        # Create route
        route = APISIXRoute(
            id="llm-chat",
            name="LLM Chat Completions",
            uri="/v1/chat/completions",
            methods=["POST"],
            upstream_id="llm-upstream",
            plugins=plugins
        )
        await client.create_route(route)
        
        print("✅ LLM Gateway configured with Langfuse observability")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(setup_llm_gateway())
```

## Troubleshooting

### Langfuse Not Receiving Traces

1. **Check API Keys**: Verify public and secret keys are correct
2. **Network Connectivity**: Ensure APISIX can reach Langfuse endpoint
3. **Plugin Configuration**: Verify plugin is enabled on routes
4. **Sampling Rate**: Check if sampling is too low

### High Latency

1. **Increase Batch Size**: Larger batches reduce overhead
2. **Increase Flush Interval**: Less frequent flushes
3. **Disable Response Body**: Reduce payload size
4. **Use Async Logging**: Langfuse plugin is non-blocking

### Missing Metadata

1. **Check Plugin Order**: Request ID should be before Langfuse
2. **Verify Headers**: Ensure headers are being captured
3. **Review Metadata Config**: Check metadata field in plugin config

## Migration from Old Client

The old monolithic `apisix_client.py` has been removed. Update your imports:

```python
# Old (deprecated)
from apisix_client import APISIXClient

# New (modular)
from apisix import APISIXClient
from apisix.plugins import PluginBuilder
from apisix.models import APISIXRoute, APISIXUpstream
```

All functionality is preserved with the same API surface.

## Resources

- **Langfuse Documentation**: https://langfuse.com/docs
- **APISIX Plugin Documentation**: https://apisix.apache.org/docs/apisix/plugins/
- **DSP Front Door README**: [README_APISIX.md](./README_APISIX.md)
- **Control Tower Integration**: [APISIX_INTEGRATION.md](./APISIX_INTEGRATION.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review APISIX logs: `docker logs apisix`
3. Check Langfuse dashboard for ingestion errors
4. Review Control Tower manifest validation
