# APISIX Client Module

Modular APISIX client for DSP Front Door with comprehensive plugin support including Langfuse observability.

## Module Structure

```
apisix/
├── __init__.py              # Package exports
├── client.py                # Main client (composition pattern)
├── models.py                # Pydantic data models
├── plugins.py               # Plugin builders
├── routes.py                # Route CRUD operations
├── upstreams.py             # Upstream CRUD operations
├── services.py              # Service CRUD operations
├── consumers.py             # Consumer CRUD operations
├── global_rules.py          # Global rules management
└── manifest_config.py       # Manifest configuration
```

## Quick Start

```python
from apisix import APISIXClient
from apisix.models import APISIXRoute, APISIXUpstream

# Initialize client
client = APISIXClient(
    admin_url="http://localhost:9180",
    admin_key="your-admin-key"
)

# Create upstream
upstream = APISIXUpstream(
    id="my-upstream",
    name="My Service",
    type="roundrobin",
    nodes={"service:8000": 1}
)
await client.create_upstream(upstream)

# Create route with plugins
route = APISIXRoute(
    id="my-route",
    name="My Route",
    uri="/api/*",
    methods=["GET", "POST"],
    upstream_id="my-upstream",
    plugins={
        **client.build_jwt_plugin(key="key", secret="secret"),
        **client.build_rate_limit_plugin(rate=100, burst=200),
        **client.build_langfuse_plugin(
            public_key="pk-lf-...",
            secret_key="sk-lf-..."
        )
    }
)
await client.create_route(route)

# Close client
await client.close()
```

## Key Features

### 1. Composition Pattern

The client uses composition to delegate operations to specialized managers:

```python
client.routes          # RouteManager
client.upstreams       # UpstreamManager
client.services        # ServiceManager
client.consumers       # ConsumerManager
client.global_rules    # GlobalRulesManager
client.manifest_config # ManifestConfigurator
client.plugins         # PluginBuilder
```

### 2. Plugin Builders

Pre-built plugin configurations:

```python
# Authentication
client.build_jwt_plugin(key, secret)

# Rate Limiting
client.build_rate_limit_plugin(rate, burst)

# CORS
client.build_cors_plugin(origins="*")

# Observability
client.build_prometheus_plugin()
client.build_langfuse_plugin(public_key, secret_key)
client.build_opentelemetry_plugin(endpoint)

# Combined
client.build_combined_observability_plugins(
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
    prometheus_enabled=True,
    request_id_enabled=True
)
```

### 3. Manifest Configuration

Configure APISIX from Control Tower manifests:

```python
# Load and apply manifest
manifest = {...}  # From Control Tower
result = await client.configure_from_manifest(manifest)

# Cleanup project resources
await client.cleanup_project_resources("project-id")

# List project resources
resources = await client.list_project_resources("project-id")
```

### 4. Resource Management

Direct CRUD operations:

```python
# Routes
await client.create_route(route)
await client.get_route(route_id)
await client.list_routes()
await client.delete_route(route_id)

# Upstreams
await client.create_upstream(upstream)
await client.get_upstream(upstream_id)
await client.list_upstreams()
await client.delete_upstream(upstream_id)

# Services
await client.create_service(service)
await client.list_services()
await client.delete_service(service_id)

# Consumers
await client.create_consumer(consumer)
await client.get_consumer(username)
await client.list_consumers()
await client.delete_consumer(username)

# Global Rules
await client.get_global_rules()
await client.set_global_rule(rule_id, plugins)
```

## Langfuse Integration

### Basic Setup

```python
# Add Langfuse to a route
langfuse_plugin = client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",
    sample_rate=1.0,
    metadata={"environment": "production"}
)

route.plugins.update(langfuse_plugin)
```

### Global Observability

```python
# Apply to all routes
global_plugins = client.build_combined_observability_plugins(
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
    prometheus_enabled=True,
    request_id_enabled=True,
    project_name="my-project"
)

await client.set_global_rule("observability", global_plugins)
```

See [APISIX_LANGFUSE_INTEGRATION.md](../../APISIX_LANGFUSE_INTEGRATION.md) for complete documentation.

## Architecture Benefits

### Before (Monolithic)
- Single 770-line file
- Hard to maintain
- Difficult to test individual components
- No clear separation of concerns

### After (Modular)
- 9 focused modules
- Each ~50-150 lines
- Easy to test and maintain
- Clear separation of concerns
- Extensible architecture

## Testing

```python
import pytest
from apisix import APISIXClient

@pytest.fixture
async def client():
    client = APISIXClient(
        admin_url="http://localhost:9180",
        admin_key="test-key"
    )
    yield client
    await client.close()

async def test_create_route(client):
    route = APISIXRoute(
        id="test-route",
        name="Test",
        uri="/test",
        methods=["GET"]
    )
    result = await client.create_route(route)
    assert result is not None
```

## Best Practices

1. **Always close the client**: Use async context manager or call `close()`
2. **Use plugin builders**: Don't manually construct plugin configs
3. **Validate manifests**: Use Control Tower validation before applying
4. **Monitor health**: Use `client.health_check()` regularly
5. **Handle errors**: Wrap operations in try-except blocks
6. **Use environment variables**: For sensitive data like API keys

## Examples

See the parent directory for complete examples:
- [APISIX_LANGFUSE_INTEGRATION.md](../../APISIX_LANGFUSE_INTEGRATION.md)
- [APISIX_INTEGRATION.md](../../APISIX_INTEGRATION.md)
- [README_APISIX.md](../../README_APISIX.md)
