# APISIX Project-Based Organization

## Overview

The enhanced APISIX integration now provides clear project-based organization for all resources created from Control Tower manifests. Each manifest/project creates a structured set of APISIX resources that are easily identifiable and manageable.

## Organization Strategy

### 1. Project Namespacing
All APISIX resources are prefixed with the `project_id` from the manifest:
- **Routes**: `{project_id}-{route_name}`
- **Services**: `{project_id}-service`
- **Upstreams**: `{project_id}-{upstream_name}`
- **Consumers**: `{project_id}-consumer`
- **Global Rules**: `{project_id}-global-plugins`

### 2. APISIX Services
Each project gets its own APISIX Service that groups all related routes:
```json
{
  "id": "my-project-service",
  "name": "my-project-api-service",
  "desc": "API Service for My Project - Environment: production",
  "upstream_id": "my-project-backend"
}
```

### 3. APISIX Consumers
Each project gets a dedicated consumer for authentication and access control:
```json
{
  "username": "my-project-consumer",
  "desc": "Consumer for project: My Project (production)",
  "plugins": {
    "jwt-auth": {
      "key": "my-project-key",
      "secret": "jwt-secret-from-manifest",
      "algorithm": "HS256",
      "exp": 1800
    }
  }
}
```

### 4. Route URIs
Routes are automatically prefixed with the project ID to avoid conflicts:
- Original route: `/api/users`
- Transformed route: `/my-project/api/users`

### 5. Metadata Tracking
All routes include metadata to track their source:
```json
{
  "plugins": {
    "metadata": {
      "project_id": "my-project",
      "project_name": "My Project",
      "environment": "production",
      "manifest_version": "1.0.0"
    }
  }
}
```

## API Endpoints

### List All Resources for a Project
```bash
GET /admin/apisix/projects/{project_id}/resources
```

Response:
```json
{
  "routes": [
    {
      "name": "my-project-echo-route",
      "uri": "/my-project/test/echo",
      "methods": ["GET", "POST"],
      "service_id": "my-project-service",
      "desc": "Route for My Project - echo-route"
    }
  ],
  "upstreams": [...],
  "services": [...],
  "consumers": [...],
  "summary": {
    "project_id": "my-project",
    "total_routes": 2,
    "total_upstreams": 1,
    "total_services": 1,
    "total_consumers": 1
  }
}
```

### Clean Up Project Resources
```bash
DELETE /admin/apisix/projects/{project_id}/resources
```

Response:
```json
{
  "deleted_routes": 2,
  "deleted_upstreams": 1,
  "deleted_services": 1,
  "deleted_consumers": 1,
  "errors": []
}
```

### List All Services
```bash
GET /admin/apisix/services
```

### List All Consumers
```bash
GET /admin/apisix/consumers
```

## Example Manifest Configuration

```json
{
  "project_id": "ai-chatbot",
  "project_name": "AI Chatbot Service",
  "environment": "production",
  "modules": [
    {
      "module_type": "jwt_config",
      "name": "chatbot-auth",
      "config": {
        "secret_key": "my-jwt-secret",
        "algorithm": "HS256",
        "expiration_minutes": 30
      }
    },
    {
      "module_type": "api_gateway",
      "name": "chatbot-apisix-gateway",
      "config": {
        "routes": [
          {
            "name": "chat-endpoint",
            "uri": "/api/chat",
            "methods": ["POST"],
            "plugins": [
              {
                "name": "jwt-auth",
                "enabled": true
              },
              {
                "name": "limit-req",
                "enabled": true,
                "config": {
                  "rate": 10,
                  "burst": 5
                }
              }
            ]
          }
        ],
        "upstreams": [
          {
            "name": "chatbot-backend",
            "type": "roundrobin",
            "nodes": {
              "chatbot-service:8000": 1
            }
          }
        ]
      }
    }
  ]
}
```

## APISIX Resources Created

For the above manifest, the following APISIX resources will be created:

### 1. Consumer
- **Username**: `ai-chatbot-consumer`
- **JWT Key**: `ai-chatbot-key`
- **Description**: "Consumer for project: AI Chatbot Service (production)"

### 2. Service
- **ID**: `ai-chatbot-service`
- **Name**: `ai-chatbot-api-service`
- **Description**: "API Service for AI Chatbot Service - Environment: production"

### 3. Upstream
- **ID**: `ai-chatbot-chatbot-backend`
- **Name**: `ai-chatbot-chatbot-backend`

### 4. Route
- **ID**: `ai-chatbot-chat-endpoint`
- **Name**: `ai-chatbot-chat-endpoint`
- **URI**: `/ai-chatbot/api/chat`
- **Service ID**: `ai-chatbot-service`
- **Description**: "Route for AI Chatbot Service - chat-endpoint"

## Benefits

1. **Clear Organization**: All resources are prefixed with project ID for easy identification
2. **No Conflicts**: Project-specific URIs prevent route conflicts between projects
3. **Easy Management**: Can list or delete all resources for a project with a single API call
4. **Service Grouping**: Routes are grouped under project-specific services
5. **Consumer Isolation**: Each project has its own consumer for authentication
6. **Metadata Tracking**: All resources include metadata about their source manifest
7. **Environment Support**: Resources include environment information for multi-environment deployments

## Best Practices

1. **Use Descriptive Project IDs**: Choose meaningful project IDs that clearly identify the service
2. **Include Environment**: Always specify the environment in manifests
3. **Version Your Manifests**: Use semantic versioning for manifest versions
4. **Regular Cleanup**: Use the cleanup endpoint to remove resources for deprecated projects
5. **Monitor Resources**: Regularly check project resources to ensure they match expectations

## Viewing Resources in APISIX Dashboard

When viewing resources in the APISIX Dashboard:

1. **Routes**: Look for routes starting with your project ID
2. **Services**: Filter services by project ID prefix
3. **Consumers**: Search for consumers with format `{project_id}-consumer`
4. **Upstreams**: Identify upstreams by project ID prefix

## Troubleshooting

### Issue: Routes not accessible
- Check if the route URI includes the project ID prefix
- Verify the service is correctly linked to the route
- Ensure the consumer has proper JWT configuration

### Issue: Authentication failures
- Verify the JWT key matches: `{project_id}-key`
- Check if the consumer was created successfully
- Ensure JWT secret matches between manifest and consumer

### Issue: Resource cleanup incomplete
- Check the API response for specific errors
- Manually verify remaining resources in APISIX Dashboard
- Use individual delete endpoints if needed

## Migration from Old Structure

If you have existing APISIX resources without project organization:

1. **Backup Current Configuration**: Export current APISIX configuration
2. **Clean Up Old Resources**: Manually remove old routes, services, upstreams
3. **Re-sync from Control Tower**: Trigger a new sync to create organized resources
4. **Verify New Structure**: Use the project resources endpoint to verify creation
