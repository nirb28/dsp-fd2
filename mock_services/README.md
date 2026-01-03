# Mock Services

This folder contains mock services for testing and development purposes. These mocks simulate external APIs and services to enable local testing without requiring actual external dependencies.

**Mock services are automatically integrated into the main Front Door application** and available at:
- HTTPBin Mock: `http://localhost:8080/mock/httpbin/*`
- OpenAI Mock: `http://localhost:8080/mock/openai/*`

No separate processes needed - just start the Front Door and the mocks are available!

## Available Mock Services

### 1. HTTPBin Mock

Simulates the popular [httpbin.org](https://httpbin.org) HTTP testing service.

**Base Path:** `/mock/httpbin`

**Endpoints:**
- `GET /get` - Returns GET request data
- `POST /post` - Returns POST request data
- `PUT /put` - Returns PUT request data
- `DELETE /delete` - Returns DELETE request data
- `GET /headers` - Returns request headers
- `GET|POST|PUT|DELETE /status/<code>` - Returns specified HTTP status code
- `GET /delay/<seconds>` - Delays response by specified seconds (max 10)
- `GET /basic-auth/<username>/<password>` - Tests basic authentication
- `GET /bearer` - Tests bearer token authentication
- `GET /json` - Returns sample JSON data
- `GET /uuid` - Returns a random UUID
- `GET /base64/<value>` - Decodes base64 string
- `GET|POST /response-headers` - Returns custom response headers
- `GET|POST|PUT|DELETE|PATCH /anything` - Returns anything sent in request
- `GET /health` - Health check endpoint

**Example Requests:**
```bash
# Start Front Door first
python run.py

# Then test mock endpoints
curl http://localhost:8080/mock/httpbin/get?param1=value1
curl -X POST http://localhost:8080/mock/httpbin/post -H "Content-Type: application/json" -d '{"key":"value"}'
curl http://localhost:8080/mock/httpbin/status/404
```

### 2. OpenAI Mock

Simulates the OpenAI API, specifically the Chat Completions endpoint.

**Base Path:** `/mock/openai`

**Endpoints:**
- `POST /v1/chat/completions` - Chat completions (supports streaming)
- `GET /v1/models` - List available models
- `GET /v1/models/<model_id>` - Get specific model details
- `POST /v1/completions` - Text completions (legacy)
- `POST /v1/embeddings` - Generate embeddings
- `GET /health` - Health check endpoint

**Features:**
- Supports streaming responses (`stream: true`)
- Supports non-streaming responses
- Mock token usage statistics
- Compatible with OpenAI Python SDK

**Example Request (Non-Streaming):**
```bash
curl http://localhost:8080/mock/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Example Request (Streaming):**
```bash
curl http://localhost:8080/mock/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

**Python SDK Usage:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/mock/openai/v1",
    api_key="mock-key"  # Any value works
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

**Streaming Example:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/mock/openai/v1",
    api_key="mock-key"
)

stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Running Mock Services

Mock services are **automatically included** when you start the Front Door:

```bash
python run.py
```

The mock endpoints are immediately available at:
- `http://localhost:8080/mock/httpbin/*`
- `http://localhost:8080/mock/openai/*`

## Integration with Front Door

These mock services can be used with the Front Door for testing routing and module integration:

1. Configure Front Door to route to mock services
2. Test APISIX integration with mock backends
3. Validate JWT authentication flows
4. Test rate limiting and other plugins

**Example Front Door Configuration:**
```json
{
  "modules": [
    {
      "name": "httpbin-test",
      "type": "inference_endpoint",
      "config": {
        "endpoint": "http://localhost:8080/mock/httpbin"
      }
    },
    {
      "name": "openai-mock",
      "type": "inference_endpoint",
      "config": {
        "endpoint": "http://localhost:8080/mock/openai/v1"
      }
    }
  ]
}
```

## Health Checks

All mock services provide health check endpoints:

```bash
curl http://localhost:8080/mock/httpbin/health
curl http://localhost:8080/mock/openai/health
```

## Dependencies

Mock services are integrated into FastAPI and use:
- FastAPI (already included in Front Door)
- Standard Python libraries (json, time, uuid, base64, datetime, asyncio)

## Development Notes

- Mock services are designed for testing only
- Responses are simplified and may not include all OpenAI API fields
- No actual AI processing occurs - responses are generated from templates
- Streaming responses simulate word-by-word generation with delays
- No authentication is enforced (any API key works for OpenAI mock)

## Future Enhancements

Potential additions:
- Anthropic Claude API mock
- Cohere API mock
- HuggingFace API mock
- Groq API mock
- Custom response templates
- Configurable response delays
- Request/response logging
- Error simulation modes
