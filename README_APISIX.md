# DSP-FD2 with APISIX Integration

## Overview

Enhanced Front Door service that integrates with Apache APISIX API Gateway for enterprise-grade routing, authentication, rate limiting, and observability of AI/LLM services.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Access to Control Tower service

### 2. Configuration

Create `.env` file:

```bash
# Control Tower
CONTROL_TOWER_URL=http://control-tower:8081
SUPERUSER_USERNAME=admin
SUPERUSER_PASSWORD=admin123

# APISIX
APISIX_ADMIN_URL=http://apisix:9180
APISIX_ADMIN_KEY=edd1c9f034335f136f87ad84b625c8f1
APISIX_GATEWAY_URL=http://apisix:9080

# JWT
JWT_SECRET_KEY=your-secret-key-minimum-256-bits

# Environment
ENVIRONMENT=production
AUTO_CONFIGURE_ROUTES=true
```

### 3. Start Services

```bash
# Start all services with APISIX
docker-compose -f docker-compose-apisix.yml up -d

# Check service health
curl http://localhost:8080/health

# View logs
docker-compose -f docker-compose-apisix.yml logs -f
```

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         Control Tower           │
                    │   (Manifest Configuration)      │
                    └──────────────┬──────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────┐
                    │         Front Door              │
                    │   (APISIX Configuration)        │
                    └──────────────┬──────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   APISIX     │  │   APISIX     │  │   APISIX     │
        │   Route 1    │  │   Route 2    │  │   Route N    │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                │                 │                  │
                ▼                 ▼                  ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ LLM Service  │  │ LLM Service  │  │ LLM Service  │
        │   Node 1     │  │   Node 2     │  │   Node N     │
        └──────────────┘  └──────────────┘  └──────────────┘
```

## Key Features

### 1. Automatic Route Configuration

Front Door automatically syncs manifests from Control Tower and configures APISIX routes:

```python
# Automatic sync on startup
AUTO_CONFIGURE_ROUTES=true

# Manual sync
curl -X POST http://localhost:8080/admin/apisix/sync
```

### 2. JWT Authentication

All routes can be protected with JWT authentication:

```python
import jwt
from datetime import datetime, timedelta

# Generate token
token = jwt.encode({
    "sub": "user123",
    "exp": datetime.utcnow() + timedelta(hours=1),
    "iss": "frontdoor-ai-gateway",
    "aud": "ai-services",
    "metadata_filter": {
        "access_level": "premium"
    }
}, SECRET_KEY, algorithm="HS256")

# Use token in requests
headers = {"Authorization": f"Bearer {token}"}
```

### 3. Rate Limiting

Configure rate limits per route or globally:

```json
{
  "name": "limit-req",
  "config": {
    "rate": 100,      // Requests per second
    "burst": 50,      // Burst capacity
    "key": "consumer_name"  // Rate limit key
  }
}
```

### 4. Load Balancing

Automatic load balancing across LLM service nodes:

```json
{
  "name": "llm-cluster",
  "type": "roundrobin",  // or "chash", "least_conn"
  "nodes": {
    "llm-1:8080": 100,   // Weight: 100
    "llm-2:8080": 100,
    "llm-3:8080": 50     // Weight: 50 (receives less traffic)
  }
}
```

## API Reference

### Admin Endpoints

#### Get APISIX Status
```http
GET /admin/apisix/status
```

Response:
```json
{
  "status": "healthy",
  "routes_count": 5,
  "upstreams_count": 2,
  "configured_projects": ["project1", "project2"]
}
```

#### Sync Manifests
```http
POST /admin/apisix/sync
```

#### Configure Project
```http
POST /admin/apisix/configure/{project_id}
```

#### List Routes
```http
GET /admin/apisix/routes
```

#### List Upstreams
```http
GET /admin/apisix/upstreams
```

### Gateway Endpoints

All other endpoints are routed through APISIX based on configured routes.

## Manifest Configuration

Example manifest with APISIX configuration:

```json
{
  "project_id": "my-ai-service",
  "modules": [
    {
      "module_type": "api_gateway",
      "name": "apisix-gateway",
      "config": {
        "routes": [
          {
            "name": "chat-completion",
            "uri": "/v1/chat/completions",
            "methods": ["POST"],
            "upstream_id": "openai-compatible",
            "plugins": [
              {
                "name": "jwt-auth",
                "enabled": true,
                "config": {...}
              },
              {
                "name": "limit-req",
                "enabled": true,
                "config": {
                  "rate": 10,
                  "burst": 5
                }
              },
              {
                "name": "prometheus",
                "enabled": true,
                "config": {}
              }
            ]
          }
        ],
        "upstreams": [
          {
            "name": "openai-compatible",
            "type": "roundrobin",
            "nodes": {
              "vllm:8000": 100
            },
            "timeout": {
              "connect": 10,
              "send": 60,
              "read": 300
            }
          }
        ],
        "global_plugins": [
          {
            "name": "cors",
            "enabled": true,
            "config": {
              "allow_origins": "*",
              "allow_methods": "*"
            }
          }
        ]
      }
    }
  ]
}
```

## Plugin Configuration

### Available Plugins

| Category | Plugin | Description |
|----------|--------|-------------|
| **Authentication** | jwt-auth | JWT token validation |
| | key-auth | API key authentication |
| | basic-auth | Basic authentication |
| **Traffic Control** | limit-req | Request rate limiting |
| | limit-count | Request count limiting |
| | limit-conn | Connection limiting |
| | api-breaker | Circuit breaker |
| **Transformation** | proxy-rewrite | Request transformation |
| | response-rewrite | Response transformation |
| **Observability** | prometheus | Metrics collection |
| | request-id | Request ID injection |
| | http-logger | HTTP request logging |
| | opentelemetry | Distributed tracing |
| **Security** | cors | CORS handling |
| | ip-restriction | IP whitelist/blacklist |
| | csrf | CSRF protection |

### Plugin Examples

#### JWT Authentication
```json
{
  "name": "jwt-auth",
  "config": {
    "key": "user-key",
    "secret": "${JWT_SECRET}",
    "algorithm": "HS256",
    "exp": 3600
  }
}
```

#### Rate Limiting
```json
{
  "name": "limit-req",
  "config": {
    "rate": 100,
    "burst": 50,
    "key_type": "var",
    "key": "remote_addr"
  }
}
```

#### Request Logging
```json
{
  "name": "http-logger",
  "config": {
    "uri": "http://log-server:8080",
    "batch_max_size": 1000,
    "include_req_body": true
  }
}
```

## Monitoring

### Prometheus Metrics

Access metrics at `http://localhost:9091/metrics`:

- `apisix_http_status` - HTTP status codes
- `apisix_http_latency` - Request latency
- `apisix_bandwidth` - Bandwidth usage
- `apisix_nginx_http_current_connections` - Active connections

### Grafana Dashboard

Access at `http://localhost:3000` (admin/admin):

1. Import dashboard from `grafana-dashboards/apisix.json`
2. Configure Prometheus data source
3. View real-time metrics

### Health Checks

```bash
# Front Door health
curl http://localhost:8080/health

# APISIX health (through Admin API)
curl -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
     http://localhost:9180/apisix/admin/routes
```

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run without Docker
python src/front_door_apisix.py

# Run tests
python test_apisix_integration.py
```

### Adding New Routes

1. Update manifest in Control Tower
2. Sync configuration:
   ```bash
   curl -X POST http://localhost:8080/admin/apisix/sync
   ```
3. Verify route creation:
   ```bash
   curl http://localhost:8080/admin/apisix/routes
   ```

### Custom Plugins

Create custom APISIX plugins for AI-specific features:

1. Write plugin in Lua
2. Add to APISIX plugin directory
3. Configure in manifest

## Troubleshooting

### Route Not Working

1. Check route configuration:
   ```bash
   curl http://localhost:8080/admin/apisix/routes
   ```

2. Verify upstream health:
   ```bash
   curl http://localhost:8080/admin/apisix/upstreams
   ```

3. Check APISIX logs:
   ```bash
   docker logs apisix
   ```

### Authentication Issues

1. Verify JWT secret matches
2. Check token expiration
3. Validate token structure:
   ```python
   import jwt
   decoded = jwt.decode(token, SECRET, algorithms=["HS256"])
   print(decoded)
   ```

### Rate Limiting Issues

1. Check current rate limit status in response headers:
   - `X-RateLimit-Limit`
   - `X-RateLimit-Remaining`
   - `X-RateLimit-Reset`

2. Review rate limit configuration
3. Check rate limit key (IP, user, etc.)

## Performance Tuning

### APISIX Configuration

```yaml
# nginx.conf optimizations
worker_connections: 10620
keepalive_requests: 1000
keepalive_timeout: 60s

# Buffer settings for LLM
proxy_buffer_size: 16k
proxy_buffers: 8 32k
client_max_body_size: 100m

# Streaming for LLM responses
proxy_buffering: "off"
```

### Upstream Optimization

```json
{
  "timeout": {
    "connect": 10,
    "send": 60,
    "read": 300  // Increased for LLM responses
  },
  "retries": 2,
  "health_check": {
    "active": {
      "healthy": {
        "interval": 2,
        "successes": 2
      },
      "unhealthy": {
        "interval": 1,
        "http_failures": 2
      }
    }
  }
}
```

## Security Best Practices

1. **Use strong JWT secrets** (minimum 256 bits)
2. **Enable TLS** for production deployments
3. **Restrict Admin API access** by IP
4. **Implement rate limiting** on all endpoints
5. **Enable request validation** for API inputs
6. **Use CORS** appropriately
7. **Monitor for anomalies** with Prometheus/Grafana
8. **Regular security audits** of configurations

## Support

For issues or questions:
1. Check the [documentation](./APISIX_INTEGRATION.md)
2. Review [test scripts](./test_apisix_integration.py)
3. Check APISIX [official docs](https://apisix.apache.org/docs/)
