# Front Door JWT Token Endpoint

## Overview

The Front Door now provides a direct endpoint to obtain JWT tokens using configuration from Control Tower manifests. This eliminates the need to manually fetch manifests and call the JWT service separately.

## Endpoint

```
POST /{project_id}/{jwt_module_name}/token
```

### URL Pattern

- `{project_id}`: The project ID from Control Tower (e.g., `sas2py`)
- `{jwt_module_name}`: The name of the JWT module in the manifest (e.g., `simple-auth`)

### Request Body

```json
{
  "username": "user",
  "password": "password"
}
```

### Response

```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi..."
}
```

## How It Works

1. **Front Door receives request** at `/{project_id}/{jwt_module_name}/token`
2. **Fetches manifest** from Control Tower for the specified project
3. **Finds JWT module** by name in the manifest
4. **Extracts configuration** including `service_url` and claims
5. **Forwards to JWT service** with `api_key_config` payload containing the JWT module config
6. **Returns tokens** to the client

## Flow Diagram

```
Client
  │
  │ POST /sas2py/simple-auth/token
  │ { "username": "admin", "password": "password" }
  │
  ▼
Front Door (Port 8080)
  │
  │ 1. Get manifest from Control Tower
  │    GET /manifests/sas2py?resolve_env=true
  │
  ▼
Control Tower (Port 8000)
  │
  │ Returns manifest with JWT module config
  │
  ▼
Front Door
  │
  │ 2. Extract JWT module "simple-auth"
  │ 3. Get service_url and config
  │ 4. Forward to JWT service
  │    POST {service_url}/token
  │    {
  │      "username": "admin",
  │      "password": "password",
  │      "api_key_config": {jwt_module.config}
  │    }
  │
  ▼
JWT Service (Port 5000)
  │
  │ Generate token with inline config
  │
  ▼
Front Door
  │
  │ Return tokens
  │
  ▼
Client
```

## Example Usage

### Using curl

```bash
curl -X POST http://localhost:8080/sas2py/simple-auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password"
  }'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8080/sas2py/simple-auth/token",
    json={
        "username": "admin",
        "password": "password"
    }
)

token_data = response.json()
access_token = token_data["access_token"]
print(f"Token: {access_token}")
```

### Using httpx (async)

```python
import httpx

async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/sas2py/simple-auth/token",
            json={
                "username": "admin",
                "password": "password"
            }
        )
        return response.json()
```

## Manifest Configuration

The JWT module in the Control Tower manifest must include:

1. **`service_url`**: URL of the JWT service
2. **Claims configuration**: Static and/or dynamic claims

### Example Manifest

```json
{
  "project_id": "sas2py",
  "modules": [
    {
      "module_type": "jwt_config",
      "name": "simple-auth",
      "config": {
        "id": "sas2py-jwt-config",
        "owner": "SAS2PY Team",
        "service_url": "http://localhost:5000",
        "claims": {
          "static": {
            "key": "sas2py-consumer-key",
            "tier": "standard",
            "models": ["llama-3.1-70b-versatile"],
            "rate_limit": 100,
            "project": "sas2py",
            "environment": "development",
            "exp_hours": 1
          }
        }
      }
    }
  ]
}
```

### With Environment Variables

```json
{
  "module_type": "jwt_config",
  "name": "simple-auth",
  "config": {
    "service_url": "${environments.${environment}.urls.jwt_service_url}",
    "claims": {
      "static": {
        "key": "sas2py-consumer-key",
        "environment": "${environment}",
        "exp_hours": 1
      }
    }
  },
  "environments": {
    "development": {
      "urls": {
        "jwt_service_url": "http://localhost:5000"
      }
    },
    "production": {
      "urls": {
        "jwt_service_url": "https://jwt.example.com"
      }
    }
  }
}
```

## Benefits

### 1. **Simplified Client Code**
No need to:
- Fetch manifest from Control Tower
- Parse JWT module configuration
- Call JWT service separately

### 2. **Centralized Configuration**
JWT configuration is managed in Control Tower manifests, not hardcoded in clients.

### 3. **Environment-Aware**
Automatically uses environment-specific configurations (dev, staging, prod).

### 4. **Consistent with Architecture**
Follows the DSP AI architecture pattern where Front Door is the entry point.

### 5. **Dynamic Configuration**
JWT claims are configured per project/module, enabling multi-tenant scenarios.

## Error Handling

### Project Not Found (404)
```json
{
  "detail": "Project sas2py not found"
}
```

### JWT Module Not Found (404)
```json
{
  "detail": "JWT module 'simple-auth' not found in project sas2py"
}
```

### Service URL Not Configured (500)
```json
{
  "detail": "JWT service URL not configured in module simple-auth"
}
```

### JWT Service Error (varies)
The error from the JWT service is passed through:
```json
{
  "detail": {
    "error": "Invalid username or password"
  }
}
```

## Testing

### Test Script

The `test_sas2py_manifest.py` includes a test for this endpoint:

```python
async def get_jwt_token() -> str:
    """Get JWT token via Front Door using manifest configuration"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{FRONT_DOOR_URL}/sas2py/simple-auth/token",
            json={
                "username": "admin",
                "password": "password"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None
```

Run the test:
```bash
python test_sas2py_manifest.py
```

## Integration with APISIX

The tokens generated through this endpoint are compatible with APISIX JWT authentication:

1. **Token contains required claims** (e.g., `key` for consumer matching)
2. **Signed with correct secret** (from manifest configuration)
3. **Ready to use** with APISIX-protected routes

### Example Flow

```bash
# 1. Get token via Front Door
TOKEN=$(curl -s -X POST http://localhost:8080/sas2py/simple-auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# 2. Use token with APISIX-protected endpoint
curl -X POST http://localhost:8080/sas2py/convert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "converter",
    "user_input": "DATA work.test; INPUT x y; DATALINES; 1 2; RUN;"
  }'
```

## Comparison: Before vs After

### Before (Manual Process)

```python
# Step 1: Get manifest
manifest = requests.get(
    "http://localhost:8000/manifests/sas2py?resolve_env=true"
).json()

# Step 2: Extract JWT config
jwt_module = next(
    m for m in manifest["modules"] 
    if m["name"] == "simple-auth"
)
jwt_config = jwt_module["config"]

# Step 3: Call JWT service
token = requests.post(
    "http://localhost:5000/token",
    json={
        "username": "admin",
        "password": "password",
        "api_key_config": jwt_config
    }
).json()["access_token"]
```

### After (Single Call)

```python
token = requests.post(
    "http://localhost:8080/sas2py/simple-auth/token",
    json={
        "username": "admin",
        "password": "password"
    }
).json()["access_token"]
```

## Related Documentation

- [API_KEY_CONFIG_PAYLOAD.md](../dsp_ai_jwt/API_KEY_CONFIG_PAYLOAD.md) - JWT service inline config feature
- [APISIX_INTEGRATION.md](APISIX_INTEGRATION.md) - APISIX integration details
- Control Tower manifest system documentation
