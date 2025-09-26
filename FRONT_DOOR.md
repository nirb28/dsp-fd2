# Front Door Service

## Overview

The Front Door Service (`front_door.py`) intelligently combines both direct module routing and APISIX gateway routing into a single service. It automatically determines the appropriate routing method based on the presence of an APISIX API gateway module in the project manifest.

## Key Features

### 1. Intelligent Routing Detection
- **Automatic Mode Selection**: Analyzes each project manifest to determine routing mode
- **APISIX Detection**: Looks for `api_gateway` modules with "apisix" in the name
- **Fallback Support**: Defaults to direct routing if no APISIX module is found

### 2. Dual Routing Modes

#### APISIX Gateway Routing
Used when manifest contains an APISIX gateway module:
- Routes requests through APISIX gateway
- Leverages gateway features: JWT auth, rate limiting, load balancing
- Automatic APISIX configuration from manifest
- Project-based resource organization

#### Direct Module Routing
Used when no APISIX gateway module is present:
- Routes requests directly to backend modules
- Dynamic module loading and management
- Module pooling for performance
- Lower latency (no gateway overhead)

### 3. Unified Management
- Single service handles both routing modes
- Consistent API for all projects
- Centralized configuration and monitoring
- Seamless switching between modes

## Architecture

```
                    ┌─────────────────────────┐
                    │   Unified Front Door    │
                    │                         │
                    │  ┌─────────────────┐   │
                    │  │ Routing Decision│   │
                    │  └────────┬────────┘   │
                    │           │             │
                    │    Has APISIX Module?   │
                    │      ┌────┴────┐        │
                    │      │         │        │
                    │     Yes       No        │
                    │      │         │        │
                    │  ┌───▼───┐ ┌──▼───┐   │
                    │  │APISIX │ │Direct│   │
                    │  │Router │ │Router│   │
                    │  └───┬───┘ └──┬───┘   │
                    └──────┼────────┼────────┘
                           │        │
                    ┌──────▼──┐    │
                    │  APISIX  │    │
                    │  Gateway │    │
                    └──────┬──┘    │
                           │        │
                    ┌──────▼────────▼──────┐
                    │   Backend Services   │
                    └──────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Control Tower
CONTROL_TOWER_URL=http://localhost:8081
CONTROL_TOWER_SECRET=your-secret

# APISIX (optional - only needed for APISIX routing)
APISIX_ADMIN_URL=http://apisix:9180
APISIX_ADMIN_KEY=edd1c9f034335f136f87ad84b625c8f1
APISIX_GATEWAY_URL=http://apisix:9080

# Module Management
MODULE_POOL_SIZE=10

# General Settings
ENVIRONMENT=production
REDIS_URL=redis://localhost:6379
AUTO_CONFIGURE_APISIX=true
CACHE_TTL=300
```

### Configuration Model

```python
class UnifiedFrontDoorConfig:
    control_tower_url: str           # Control Tower API URL
    control_tower_secret: str         # Auth secret for Control Tower
    apisix_admin_url: str            # APISIX Admin API URL (optional)
    apisix_admin_key: str            # APISIX Admin key (optional)
    apisix_gateway_url: str          # APISIX Gateway URL (optional)
    module_pool_size: int = 10       # Max modules in memory
    environment: str = "production"   # Current environment
    redis_url: str                   # Redis for caching (optional)
    auto_configure_apisix: bool = True  # Auto-sync on startup
    cache_ttl: int = 300             # Cache TTL in seconds
```

## Routing Decision Logic

The service determines routing mode using the following logic:

```python
def determine_routing_mode(manifest):
    modules = manifest.get("modules", [])
    
    for module in modules:
        module_type = module.get("module_type", "").lower()
        module_name = module.get("name", "").lower()
        
        # Check for APISIX gateway module
        if module_type == "api_gateway" and "apisix" in module_name:
            return RoutingMode.APISIX
    
    return RoutingMode.DIRECT
```

## API Endpoints

### Health & Status
- `GET /health` - Health check with routing statistics
- `GET /status` - Detailed service status

### Admin Endpoints
- `POST /admin/sync` - Sync all manifests from Control Tower
- `POST /admin/configure/{project_id}` - Configure specific project
- `GET /admin/projects` - List all projects and their routing modes
- `GET /admin/apisix/projects/{project_id}/resources` - List APISIX resources (APISIX projects only)

### Request Routing
- `/{project_id}/*` - Route requests based on project configuration

## Example Manifests

### APISIX Routing Manifest
```json
{
  "project_id": "api-service",
  "modules": [
    {
      "module_type": "api_gateway",
      "name": "api-apisix-gateway",
      "config": {
        "routes": [...],
        "upstreams": [...]
      }
    }
  ]
}
```
→ Routes through APISIX gateway

### Direct Routing Manifest
```json
{
  "project_id": "ml-service",
  "modules": [
    {
      "module_type": "inference_endpoint",
      "name": "ml-model",
      "config": {
        "endpoint": "http://ml-backend:8000"
      }
    }
  ]
}
```
→ Routes directly to module

## Usage Examples

### 1. Start the Unified Service

```bash
# Run the unified front door
python src/front_door_unified.py
```

### 2. Check Service Status

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "service": "dsp-fd2-unified",
  "status": "healthy",
  "routing_modes": {
    "apisix": ["api-service", "auth-service"],
    "direct": ["ml-service", "data-processor"]
  },
  "apisix": {
    "status": "healthy"
  },
  "modules": {
    "loaded": 2,
    "pool_size": 10
  }
}
```

### 3. List Projects

```bash
curl http://localhost:8080/admin/projects
```

Response:
```json
{
  "projects": {
    "api-service": {
      "routing_mode": "apisix",
      "apisix_configured": true
    },
    "ml-service": {
      "routing_mode": "direct",
      "apisix_configured": false
    }
  },
  "total": 2
}
```

### 4. Make Requests

```bash
# Request to APISIX-routed project
curl http://localhost:8080/api-service/users

# Request to directly-routed project
curl http://localhost:8080/ml-service/predict
```

## Benefits

### 1. Flexibility
- Use simple direct routing for basic services
- Use APISIX gateway for services needing advanced features
- Mix both approaches in the same deployment

### 2. Performance
- Direct routing for low-latency requirements
- APISIX routing for scalability and advanced features

### 3. Simplicity
- Single service to manage
- Automatic configuration based on manifests
- No manual routing decisions needed

### 4. Migration Path
- Start with direct routing
- Add APISIX module when needed
- No code changes required

## Migration from Separate Services

### From `front_door.py` (Direct Only)
1. Replace `front_door.py` with `front_door_unified.py`
2. Existing manifests continue to work with direct routing
3. Add APISIX modules to manifests as needed

### From `front_door_apisix.py` (APISIX Only)
1. Replace `front_door_apisix.py` with `front_door_unified.py`
2. Ensure manifests have `api_gateway` modules with "apisix" in name
3. Projects without APISIX modules now get direct routing

## Best Practices

### 1. When to Use APISIX Routing
- Need JWT authentication
- Require rate limiting
- Need load balancing
- Want API gateway features
- External-facing APIs
- Multi-service architectures

### 2. When to Use Direct Routing
- Internal services
- Low-latency requirements
- Simple request/response patterns
- Python-only modules
- Development/testing

### 3. Manifest Design
- Clearly name APISIX modules with "apisix" in the name
- Keep module types consistent
- Document routing requirements

### 4. Performance Optimization
- Use Redis for caching when available
- Adjust `MODULE_POOL_SIZE` based on memory
- Monitor module health checks

## Troubleshooting

### Issue: Project using wrong routing mode
- Check manifest for `api_gateway` module with "apisix" in name
- Verify APISIX configuration in environment variables
- Use `/admin/configure/{project_id}` to reconfigure

### Issue: APISIX routes not created
- Ensure APISIX is running and accessible
- Check APISIX admin credentials
- Verify manifest structure

### Issue: Direct routing module not found
- Check `BaseModule` is available
- Verify module implementation path in manifest
- Check module pool size

### Issue: High latency
- Check if project needs direct routing instead of APISIX
- Monitor module health checks
- Verify Redis caching is working

## Monitoring

### Metrics to Track
- Projects by routing mode
- APISIX gateway health
- Module pool utilization
- Cache hit/miss rates
- Request latency by routing mode

### Health Checks
- Service health: `/health`
- APISIX health: Included in status
- Module health: Per-module health checks
- Redis connection: Logged on startup

## Future Enhancements

1. **Hybrid Routing**: Route some endpoints through APISIX, others direct
2. **Dynamic Switching**: Change routing mode without restart
3. **A/B Testing**: Test different routing modes for same project
4. **Metrics Collection**: Built-in Prometheus metrics
5. **Circuit Breakers**: Automatic failover between routing modes
