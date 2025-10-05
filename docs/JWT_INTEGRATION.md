# JWT Service Integration for DSP AI Front Door

This document describes how the Front Door integrates with the `dsp_ai_jwt` service for centralized JWT token management.

## Overview

The Front Door now supports integration with the DSP AI JWT service (`dsp_ai_jwt` project) for:
- **Token Generation**: Generate JWT tokens with custom claims and API keys
- **Token Validation**: Validate tokens against the JWT service
- **APISIX Consumer Configuration**: Automatically configure APISIX consumers with JWT authentication
- **Centralized Authentication**: Use a single JWT service across multiple projects

## Architecture

```
Client Request
     ↓
Front Door (Port 8080)
     ↓
APISIX Gateway (Port 9080)
     ↓ (JWT Validation)
JWT Service (Port 5000)
     ↓
LLM Services (Groq, OpenAI, etc.)
```

## Configuration

### 1. Manifest JWT Config Module

Add a `jwt_config` module to your Control Tower manifest:

```json
{
  "module_type": "jwt_config",
  "name": "simple-auth",
  "config": {
    "secret_key": "${environments.${environment}.secrets.jwt_secret_key}",
    "algorithm": "HS256",
    "expiration_minutes": 30,
    "issuer": "sas2py-${environment}",
    "audience": "${environment}-users",
    "refresh_token_enabled": false,
    "service_url": "${environments.${environment}.urls.jwt_service_url}"
  }
}
```

### 2. Environment Configuration

Add JWT service URL to your environment configuration:

```json
{
  "environments": {
    "development": {
      "secrets": {
        "jwt_secret_key": "${DEV_JWT_SECRET}"
      },
      "urls": {
        "jwt_service_url": "http://localhost:5000"
      }
    },
    "production": {
      "secrets": {
        "jwt_secret_key": "${PROD_JWT_SECRET}"
      },
      "urls": {
        "jwt_service_url": "https://jwt.example.com"
      }
    }
  }
}
```

## Usage

### Python Client Example

```python
from jwt_client import JWTClient

# Initialize JWT client
jwt_client = JWTClient("http://localhost:5000")

# Generate token
result = await jwt_client.generate_token(
    username="admin",
    password="your-password",
    api_key="optional-api-key"  # For additional claims
)

if result["success"]:
    access_token = result["access_token"]
    refresh_token = result["refresh_token"]
    print(f"Token: {access_token}")

# Validate token
validation = await jwt_client.validate_token(access_token)
if validation["valid"]:
    print(f"Token is valid for user: {validation['identity']}")

# Refresh token
new_token = await jwt_client.refresh_token(refresh_token)
if new_token["success"]:
    print(f"New token: {new_token['access_token']}")

await jwt_client.close()
```

### APISIX Integration

The Front Door automatically:

1. **Creates APISIX Consumers** with JWT authentication based on `jwt_config` modules
2. **Configures JWT Plugins** on routes that require authentication
3. **Syncs JWT Secrets** from the manifest to APISIX

Example APISIX consumer created:

```json
{
  "username": "sas2py_consumer",
  "desc": "JWT consumer for project: sas2py",
  "plugins": {
    "jwt-auth": {
      "key": "sas2py-key",
      "secret": "your-jwt-secret",
      "algorithm": "HS256"
    }
  }
}
```

### Making Authenticated Requests

```python
import httpx

# Get token from JWT service
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:5000/token",
        json={
            "username": "admin",
            "password": "your-password"
        }
    )
    token = response.json()["access_token"]

# Use token with Front Door/APISIX
headers = {"Authorization": f"Bearer {token}"}
response = await client.post(
    "http://localhost:8080/api/sas2py/convert",
    headers=headers,
    json={"user_input": "Your SAS code here"}
)
```

## JWT Client API Reference

### `JWTClient(jwt_service_url, default_username, default_password)`

Initialize the JWT client.

**Parameters:**
- `jwt_service_url` (str): Base URL of the JWT service
- `default_username` (str, optional): Default username for token generation
- `default_password` (str, optional): Default password for token generation

### `generate_token(username, password, api_key, custom_secret)`

Generate a JWT token.

**Parameters:**
- `username` (str, optional): Username for authentication
- `password` (str, optional): Password for authentication
- `api_key` (str, optional): API key for additional claims
- `custom_secret` (str, optional): Custom secret for token signing

**Returns:**
```python
{
    "success": True,
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "custom_secret_used": False
}
```

### `validate_token(token)`

Validate a JWT token.

**Parameters:**
- `token` (str): JWT token to validate

**Returns:**
```python
{
    "valid": True,
    "identity": "admin",
    "claims": {
        "logged_in_as": "admin",
        "groups": ["admin"],
        "roles": ["superuser"]
    }
}
```

### `refresh_token(refresh_token)`

Refresh an access token.

**Parameters:**
- `refresh_token` (str): Refresh token

**Returns:**
```python
{
    "success": True,
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### `health_check()`

Check JWT service health.

**Returns:**
```python
{
    "status": "healthy",
    "timestamp": "2025-09-30T20:00:00",
    "service_reachable": True
}
```

## Features

### 1. Custom Claims via API Keys

The JWT service supports API keys that add custom claims to tokens:

```python
result = await jwt_client.generate_token(
    username="admin",
    password="password",
    api_key="groq_api_key_123"  # Adds model access claims
)
```

### 2. Custom Secrets

Use project-specific secrets for token signing:

```python
result = await jwt_client.generate_token(
    username="admin",
    password="password",
    custom_secret="project-specific-secret"
)
```

### 3. Token Refresh

Refresh tokens without re-authentication:

```python
new_token = await jwt_client.refresh_token(refresh_token)
```

## Security Best Practices

1. **Use Environment Variables**: Store JWT secrets in environment variables, not in manifests
2. **HTTPS in Production**: Always use HTTPS for JWT service in production
3. **Token Expiration**: Set appropriate expiration times based on security requirements
4. **Secret Rotation**: Regularly rotate JWT secrets
5. **API Key Management**: Use API keys for fine-grained access control

## Troubleshooting

### Token Validation Fails

- Verify the JWT secret matches between the JWT service and APISIX consumer
- Check token expiration time
- Ensure the token is sent in the `Authorization: Bearer <token>` header

### JWT Service Unreachable

- Verify the JWT service is running on the configured port
- Check network connectivity
- Review JWT service logs for errors

### APISIX Consumer Not Created

- Ensure the manifest has a `jwt_config` module
- Check that `resolve_env=true` is used when fetching the manifest
- Review APISIX client logs for consumer creation errors

## Example: Complete Workflow

```python
import asyncio
from jwt_client import JWTClient
import httpx

async def main():
    # 1. Initialize JWT client
    jwt_client = JWTClient("http://localhost:5000")
    
    # 2. Generate token
    result = await jwt_client.generate_token(
        username="admin",
        password="dspsa_p@ssword"
    )
    
    if not result["success"]:
        print(f"Failed to get token: {result['error']}")
        return
    
    token = result["access_token"]
    
    # 3. Make authenticated request to Front Door
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/sas2py/convert",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_input": "DATA work.example; INPUT x y; DATALINES; 1 2 3 4; RUN;"
            }
        )
        
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Error:", response.status_code, response.text)
    
    # 4. Cleanup
    await jwt_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Integration with Control Tower

The Control Tower manifest system now supports:

1. **JWT Config Modules**: Define JWT authentication requirements
2. **Environment Variable Resolution**: Resolve JWT service URLs per environment
3. **Cross-References**: Link modules that depend on JWT authentication
4. **Validation**: Validate JWT configuration before deployment

See the `sas2py.json` manifest for a complete example.
