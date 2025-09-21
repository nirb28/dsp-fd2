# DSP-FD2: Dynamic Service Platform - Front Door v2

DSP-FD2 is an enterprise-grade, modular API gateway that serves as the intelligent front door for dynamic service discovery and routing. It provides a unified entry point for all AI/ML services, with automatic module loading, security enforcement, and comprehensive observability.

### Key Features

## Architecture

```
Client Request → Front Door (dsp-fd2) → Control Tower → Module Discovery → Module Execution → Backend Service
                      ↓                       ↓                              ↓
                  JWT Service            Vault Service                  Metrics/Logging
```

### Core Components

1. **Front Door Service**: Main gateway handling request routing
2. **Module Manager**: Dynamic module lifecycle management
3. **Control Tower Integration**: Manifest fetching and caching
4. **Security Layer**: JWT validation and secret management
5. **Module Interface**: Standardized contract for all modules

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (for caching)
- PostgreSQL (optional, for audit logs)

### Installation

3. **Install dependencies**:
```bash
python -m venv .fd_venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Start services with Docker Compose**:
```bash
docker-compose up -d
```

5. **Verify installation**:
```bash
curl http://localhost:8080/health
```

## 📖 Usage

### Basic Request Flow

Send requests to the Front Door with project and module information:

```bash
# OpenAI-compatible chat completion
curl -X POST http://localhost:8080/my-project/inference/v1/chat/completions \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Environment: production" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Request Routing Patterns

1. **Path-based** (Recommended):
   ```
   /{project}/{module}/endpoint
   ```

2. **Header-based**:
   ```
   X-Project-Module: project/module
   ```

3. **Subdomain-based**:
   ```
   project-module.api.company.com
   ```

## 🔧 Configuration

### Module Manifest

Modules are configured via manifests stored in the Control Tower:

```json
{
  "module_type": "inference_openai",
  "runtime": {
    "type": "python:3.11",
    "implementation": "src.modules.inference_openai.InferenceOpenAIModule"
  },
  "endpoints": {
    "dev": {
      "primary": "http://dev-llm-gateway:8080"
    },
    "prod": {
      "primary": "https://prod-llm-gateway"
    }
  },
  "configuration_references": [
    {
      "name": "api_key",
      "source": "vault://secrets/openai_key",
      "required": true
    }
  ]
}
```

### Environment Variables

Key configuration options (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTROL_TOWER_URL` | Control Tower API endpoint | `http://localhost:8081` |
| `VAULT_URL` | HashiCorp Vault endpoint | `http://localhost:8200` |
| `JWT_SERVICE_URL` | JWT validation service | `http://localhost:8082` |
| `CACHE_TTL_SECONDS` | Manifest cache duration | `300` |
| `MODULE_POOL_SIZE` | Max modules in memory | `10` |

## 🔌 Module Development

### Creating a New Module

1. **Implement the BaseModule interface**:

```python
from src.core.module_interface import BaseModule, ModuleConfig, ModuleRequest, ModuleResponse

class MyCustomModule(BaseModule):
    async def initialize(self, config: ModuleConfig) -> None:
        await super().initialize(config)
        # Your initialization logic
    
    async def handle_request(self, request: ModuleRequest) -> ModuleResponse:
        # Process request
        return ModuleResponse(
            status_code=200,
            body={"result": "success"}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy"}
    
    async def shutdown(self) -> None:
        # Cleanup resources
        await super().shutdown()
```

2. **Register in manifest**:

```json
{
  "module_type": "my_custom",
  "runtime": {
    "implementation": "src.modules.my_custom.MyCustomModule"
  }
}
```

## Monitoring

### Metrics

Prometheus metrics available at `/metrics`:

- `fd_requests_total`: Total request count
- `fd_request_duration_seconds`: Request latency
- `fd_active_requests`: Currently active requests
- `fd_module_load_seconds`: Module loading time
- `fd_cache_hit_ratio`: Cache effectiveness

### Health Checks

```bash
# Basic health
curl http://localhost:8080/health

# Detailed health with dependencies
curl http://localhost:8080/health?detailed=true
```

### Logging

Structured JSON logs with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:00:00Z",
  "level": "INFO",
  "request_id": "abc-123",
  "message": "Request processed",
  "duration": 0.042,
  "module": "inference",
  "status": 200
}
```

## Security

### Authentication

- **JWT Bearer Tokens**: Primary authentication method
- **API Keys**: Alternative for service-to-service
- **mTLS**: Optional for enhanced security

### Secret Management

All secrets are stored in HashiCorp Vault and injected at runtime:

```python
# Secrets are automatically available in module config
api_key = self.config.runtime_references.get("api_key")
```

### Rate Limiting

Configurable per-client rate limits with burst support:

```python
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10
```

## Testing

### Unit Tests
```bash
pytest tests/unit -v
```

### Integration Tests
```bash
pytest tests/integration -v
```

### Load Testing
```bash
# Using k6
k6 run tests/load/scenario.js
```

### End-to-End Testing
```bash
./scripts/e2e_test.sh
```

## Deployment

### Docker

```bash
docker build -t dsp-fd2:latest .
docker run -p 8080:8080 --env-file .env dsp-fd2:latest
```

## Roadmap

- [x] Phase 1: Basic routing and module interface
- [x] Phase 2: Control Tower integration
- [x] Phase 3: Security implementation
- [x] Phase 4: Dynamic module loading
- [x] Phase 5: OpenAI-compatible inference module
- [ ] Phase 6: Production monitoring
- [ ] Phase 7: Auto-scaling and optimization
- [ ] Phase 8: Additional module types (RAG, Data Processing, etc.)


Built with ❤️ by the DSP Platform Team
