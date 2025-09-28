curl "http://127.0.0.1:9180/apisix/admin/upstreams" -X PUT \
  -H "X-API-KEY: ${ADMIN_API_KEY}" \
  -d '{
    "id": "groq-upstream",
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "api.groq.com:443": 1
    }
  }'
  
curl "http://127.0.0.1:9180/apisix/admin/routes" -X PUT \
  -H "X-API-KEY: ${ADMIN_API_KEY}" \
  -d '{
    "id": "groq-route",
    "uri": "/groq/chat/*",
    "methods": ["POST"],
    "upstream_id": "groq-upstream",
    "plugins": {
      "proxy-rewrite": {
        "uri": "/openai/v1/chat/completions",
        "scheme": "https"
      },
      "ai-proxy": {
        "provider": "openai-compatible",
        "auth": {
          "header": {
            "Authorization": "Bearer <API_KEY>"
          }
        },
        "options": {
          "model": "llama-3.1-8b-instant"
        },
        "override": {
          "endpoint": "https://api.groq.com/openai/v1/chat/completions"
        }
      }
    }
  }'