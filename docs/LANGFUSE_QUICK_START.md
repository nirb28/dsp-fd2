# Langfuse Quick Start Guide

## 1. Get Langfuse Keys

### Option A: Cloud (Easiest)
1. Go to https://cloud.langfuse.com
2. Sign up for free account
3. Create a new project
4. Copy your **Public Key** (`pk-lf-...`) and **Secret Key** (`sk-lf-...`)

### Option B: Self-Hosted
```bash
docker run -d \
  -p 3000:3000 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/langfuse \
  -e NEXTAUTH_SECRET=your-secret \
  langfuse/langfuse:latest
```

## 2. Set Environment Variables

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com  # or http://localhost:3000
```

## 3. Add to APISIX Route

### Method 1: Single Route

```python
from apisix import APISIXClient
from apisix.models import APISIXRoute
import os

client = APISIXClient(
    admin_url="http://localhost:9180",
    admin_key="your-admin-key"
)

# Create route with Langfuse
route = APISIXRoute(
    id="llm-chat",
    name="LLM Chat",
    uri="/v1/chat/completions",
    methods=["POST"],
    upstream_id="llm-upstream",
    plugins={
        **client.build_langfuse_plugin(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        ),
        **client.build_jwt_plugin(key="auth", secret="secret")
    }
)

await client.create_route(route)
```

### Method 2: Global (All Routes)

```python
# Apply Langfuse to all routes
global_plugins = client.build_combined_observability_plugins(
    langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    prometheus_enabled=True,
    request_id_enabled=True,
    project_name="my-llm-gateway"
)

await client.set_global_rule("observability", global_plugins)
```

### Method 3: Control Tower Manifest

```json
{
  "project_id": "llm-project",
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
              "uri": "${LANGFUSE_HOST}/api/public/ingestion",
              "auth_header": "Basic ${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}",
              "batch_max_size": 100,
              "include_req_body": true,
              "include_resp_body": true
            }
          }
        ]
      }
    }
  ]
}
```

## 4. Send Test Request

```bash
# Send request through APISIX
curl -X POST http://localhost:9080/v1/chat/completions \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 5. View Traces

1. Go to Langfuse dashboard: https://cloud.langfuse.com
2. Select your project
3. Click **Traces** in sidebar
4. View your LLM request traces

## Configuration Options

### Basic (Minimal)
```python
client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-..."
)
```

### Production (Recommended)
```python
client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",
    sample_rate=1.0,              # 100% sampling
    batch_max_size=100,           # Batch 100 traces
    flush_interval=3,             # Flush every 3 seconds
    include_request_body=True,    # Capture prompts
    include_response_body=True,   # Capture completions
    metadata={
        "environment": "production",
        "region": "us-east-1",
        "team": "ml-platform"
    }
)
```

### High Volume (Optimized)
```python
client.build_langfuse_plugin(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    sample_rate=0.1,              # 10% sampling
    batch_max_size=500,           # Larger batches
    flush_interval=10,            # Less frequent flushes
    include_response_body=False   # Reduce payload size
)
```

## Common Patterns

### Pattern 1: Per-Environment Config

```python
import os

env = os.getenv("ENVIRONMENT", "development")

config = {
    "development": {
        "sample_rate": 1.0,
        "include_response_body": True
    },
    "staging": {
        "sample_rate": 0.5,
        "include_response_body": True
    },
    "production": {
        "sample_rate": 0.1,
        "include_response_body": False
    }
}

langfuse_plugin = client.build_langfuse_plugin(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    **config[env]
)
```

### Pattern 2: With Request ID Correlation

```python
plugins = {
    **client.plugins.build_request_id_plugin(
        header_name="X-Request-Id",
        algorithm="uuid"
    ),
    **client.build_langfuse_plugin(
        public_key="pk-lf-...",
        secret_key="sk-lf-..."
    )
}
```

### Pattern 3: Full Observability Stack

```python
plugins = client.build_combined_observability_plugins(
    langfuse_public_key="pk-lf-...",
    langfuse_secret_key="sk-lf-...",
    prometheus_enabled=True,      # Metrics
    request_id_enabled=True,      # Trace correlation
    project_name="llm-gateway"
)
```

## Troubleshooting

### No traces appearing?

1. **Check keys**: Verify public/secret keys are correct
2. **Check network**: Ensure APISIX can reach Langfuse
   ```bash
   docker exec apisix curl https://cloud.langfuse.com
   ```
3. **Check plugin**: Verify plugin is enabled on route
   ```bash
   curl http://localhost:9180/apisix/admin/routes/your-route-id \
     -H "X-API-KEY: your-admin-key"
   ```
4. **Check logs**: Review APISIX error logs
   ```bash
   docker logs apisix
   ```

### High latency?

1. **Increase batch size**: `batch_max_size=500`
2. **Increase flush interval**: `flush_interval=10`
3. **Disable response body**: `include_response_body=False`
4. **Reduce sampling**: `sample_rate=0.1`

### Missing metadata?

1. **Add request ID plugin**: Must be before Langfuse
2. **Check metadata config**: Verify metadata field in plugin
3. **Review headers**: Ensure headers are being captured

## Next Steps

1. ✅ Set up Langfuse account
2. ✅ Configure APISIX plugin
3. ✅ Send test requests
4. ✅ View traces in dashboard
5. 📊 Analyze performance metrics
6. 🔍 Debug issues with trace inspection
7. 📈 Set up alerts for anomalies
8. 💰 Monitor costs and usage

## Resources

- **Full Documentation**: [APISIX_LANGFUSE_INTEGRATION.md](./APISIX_LANGFUSE_INTEGRATION.md)
- **Module README**: [src/apisix/README.md](./src/apisix/README.md)
- **Langfuse Docs**: https://langfuse.com/docs
- **APISIX Docs**: https://apisix.apache.org/docs/

## Example: Complete Setup Script

```python
#!/usr/bin/env python3
"""
Setup APISIX with Langfuse observability
"""
import asyncio
import os
from apisix import APISIXClient
from apisix.models import APISIXRoute, APISIXUpstream

async def main():
    # Initialize client
    client = APISIXClient(
        admin_url=os.getenv("APISIX_ADMIN_URL", "http://localhost:9180"),
        admin_key=os.getenv("APISIX_ADMIN_KEY", "admin-key")
    )
    
    try:
        print("🚀 Setting up APISIX with Langfuse...")
        
        # Create upstream
        upstream = APISIXUpstream(
            id="llm-service",
            name="LLM Service",
            type="roundrobin",
            nodes={"llm-service:8000": 1},
            timeout={"connect": 30, "send": 300, "read": 300}
        )
        await client.create_upstream(upstream)
        print("✅ Created upstream")
        
        # Build plugins
        plugins = {
            **client.build_langfuse_plugin(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                metadata={"environment": os.getenv("ENVIRONMENT", "development")}
            ),
            **client.build_jwt_plugin(
                key="auth-key",
                secret=os.getenv("JWT_SECRET", "your-secret")
            ),
            **client.build_rate_limit_plugin(rate=100, burst=200),
            **client.build_prometheus_plugin()
        }
        print("✅ Built plugins")
        
        # Create route
        route = APISIXRoute(
            id="llm-chat",
            name="LLM Chat Completions",
            uri="/v1/chat/completions",
            methods=["POST"],
            upstream_id="llm-service",
            plugins=plugins
        )
        await client.create_route(route)
        print("✅ Created route")
        
        # Health check
        health = await client.health_check()
        print(f"✅ Health check: {health['status']}")
        
        print("\n🎉 Setup complete! Langfuse observability is now active.")
        print(f"📊 View traces at: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Save as `setup_langfuse.py` and run:
```bash
python setup_langfuse.py
```
