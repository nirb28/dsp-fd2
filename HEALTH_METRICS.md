# Health Checks and Prometheus Metrics for DSP-FD2

This document describes the health check and metrics functionality available in DSP-FD2, configured through Control Tower manifests.

## Overview

DSP-FD2 supports comprehensive health monitoring and Prometheus-compatible metrics through manifest-based configuration. This enables:

- **Health Checks**: Configurable endpoint monitoring with payload testing and response assertions
- **Prometheus Metrics**: Standard and custom metrics with full Prometheus exposition format
- **Per-Project Configuration**: Each project can have its own health check and metrics configuration
- **Kubernetes Integration**: Liveness and readiness probes for container orchestration

## Health Check Module

### Configuration

Add a `health_check` module to your Control Tower manifest:

```json
{
  "module_type": "health_check",
  "name": "platform-health",
  "config": {
    "enabled": true,
    "endpoint_path": "/health",
    "liveness_path": "/health/live",
    "readiness_path": "/health/ready",
    "check_interval_seconds": 30,
    "cache_results_seconds": 5,
    "parallel_checks": true,
    "include_details": true,
    "failure_threshold": 3,
    "success_threshold": 1,
    "response_format": "detailed",
    "targets": [...]
  }
}
```

### Health Check Targets

Each target defines a service to monitor:

```json
{
  "name": "rag-service",
  "url": "http://rag-service:8080/health",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer ${TOKEN}"
  },
  "payload": null,
  "timeout_seconds": 10,
  "expected_status_codes": [200],
  "response_json_path": "$.status",
  "expected_value": "healthy",
  "response_contains": "ok",
  "response_not_contains": "error",
  "critical": true,
  "retry_count": 2,
  "retry_delay_seconds": 1.0
}
```

### Target Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | required | Unique name for the health check target |
| `url` | string | required | URL to check |
| `method` | string | "GET" | HTTP method (GET, POST, PUT, etc.) |
| `headers` | object | {} | HTTP headers to include |
| `payload` | object | null | Request body for POST/PUT methods |
| `timeout_seconds` | int | 10 | Request timeout |
| `expected_status_codes` | array | [200] | Expected HTTP status codes |
| `response_json_path` | string | null | JSONPath to extract from response |
| `expected_value` | any | null | Expected value at JSON path |
| `response_contains` | string | null | String that response must contain |
| `response_not_contains` | string | null | String that response must NOT contain |
| `critical` | bool | true | If true, failure marks overall health as unhealthy |
| `retry_count` | int | 1 | Number of retries before marking failed |
| `retry_delay_seconds` | float | 1.0 | Delay between retries |

### Response Assertions

The health check service supports multiple assertion types:

1. **Status Code Check**: Verify the HTTP status code matches expected values
2. **JSON Path Extraction**: Extract a value from JSON response using JSONPath
3. **Value Comparison**: Compare extracted value with expected value
4. **Contains Check**: Verify response body contains a specific string
5. **Not Contains Check**: Verify response body does NOT contain a specific string

### JSONPath Support

Supported JSONPath expressions:
- `$.key` - Access object key
- `$.key.nested` - Access nested key
- `$.array[0]` - Access array element by index
- `$.array[*]` - Access all array elements

### Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Global health check |
| `GET /health/live` | Global liveness probe |
| `GET /health/ready` | Global readiness probe |
| `GET /{project_id}/health` | Project-specific health check |
| `GET /{project_id}/health/live` | Project-specific liveness probe |
| `GET /{project_id}/health/ready` | Project-specific readiness probe |

### Health Response Format

**Detailed format** (default):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "total_checks": 3,
  "healthy_checks": 3,
  "unhealthy_checks": 0,
  "checks": [
    {
      "name": "rag-service",
      "status": "healthy",
      "response_time_ms": 45.2,
      "message": "OK",
      "critical": true,
      "details": {"status_code": 200},
      "timestamp": "2024-01-15T10:00:00Z"
    }
  ]
}
```

**Simple format**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### Health Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All critical checks passing |
| `unhealthy` | One or more critical checks failing |
| `degraded` | Non-critical checks failing, critical checks passing |
| `unknown` | Unable to determine health status |

---

## Metrics Module

### Configuration

Add a `metrics` module to your Control Tower manifest:

```json
{
  "module_type": "metrics",
  "name": "platform-metrics",
  "config": {
    "enabled": true,
    "endpoint_path": "/metrics",
    "namespace": "ai_platform",
    "default_labels": {
      "environment": "production",
      "service": "ai-platform"
    },
    "enable_default_metrics": true,
    "default_metrics": [
      "request_count",
      "request_latency_seconds",
      "error_count"
    ],
    "custom_metrics": [...],
    "latency_buckets": [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    "size_buckets": [100, 1000, 10000, 100000, 1000000]
  }
}
```

### Default Metrics

The following default metrics are available:

| Metric | Type | Description |
|--------|------|-------------|
| `request_count` | Counter | Total HTTP requests |
| `request_latency_seconds` | Histogram | Request latency |
| `request_size_bytes` | Histogram | Request body size |
| `response_size_bytes` | Histogram | Response body size |
| `active_requests` | Gauge | Currently active requests |
| `error_count` | Counter | Total errors |
| `health_check_status` | Gauge | Health check status (1=healthy, 0=unhealthy) |
| `upstream_latency_seconds` | Histogram | Upstream service latency |

### Custom Metrics

Define custom metrics for your application:

```json
{
  "custom_metrics": [
    {
      "name": "rag_queries_total",
      "type": "counter",
      "description": "Total RAG queries processed",
      "labels": ["configuration", "status"]
    },
    {
      "name": "llm_inference_latency_seconds",
      "type": "histogram",
      "description": "LLM inference latency",
      "labels": ["model"],
      "buckets": [0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
    },
    {
      "name": "cache_hit_ratio",
      "type": "gauge",
      "description": "Cache hit ratio",
      "labels": ["cache_type"]
    }
  ]
}
```

### Metric Types

| Type | Description | Use Case |
|------|-------------|----------|
| `counter` | Monotonically increasing value | Request counts, error counts |
| `gauge` | Value that can go up or down | Active connections, queue size |
| `histogram` | Distribution of values | Latency, request sizes |
| `summary` | Similar to histogram with quantiles | Response times |

### Metrics Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Global Prometheus metrics |
| `GET /{project_id}/metrics` | Project-specific metrics |

### Prometheus Integration

The metrics endpoint returns Prometheus exposition format:

```
# HELP ai_platform_request_total Total number of HTTP requests
# TYPE ai_platform_request_total counter
ai_platform_request_total{environment="production",method="GET",endpoint="/query",status_code="200"} 1234

# HELP ai_platform_request_latency_seconds HTTP request latency in seconds
# TYPE ai_platform_request_latency_seconds histogram
ai_platform_request_latency_seconds_bucket{environment="production",method="GET",endpoint="/query",le="0.1"} 100
ai_platform_request_latency_seconds_bucket{environment="production",method="GET",endpoint="/query",le="0.5"} 450
ai_platform_request_latency_seconds_sum{environment="production",method="GET",endpoint="/query"} 123.45
ai_platform_request_latency_seconds_count{environment="production",method="GET",endpoint="/query"} 500
```

### Pushgateway Support

For batch jobs or short-lived processes, enable Pushgateway:

```json
{
  "pushgateway_enabled": true,
  "pushgateway_url": "http://pushgateway:9091",
  "pushgateway_job": "ai_platform",
  "push_interval_seconds": 60
}
```

---

## Kubernetes Integration

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dsp-fd2
spec:
  selector:
    matchLabels:
      app: dsp-fd2
  endpoints:
  - port: http
    path: /metrics
    interval: 15s
```

---

## Example Manifest

See `manifests/ai-platform-with-observability.json` in the Control Tower repository for a complete example.

## Dependencies

The metrics service requires `prometheus_client`:

```bash
pip install prometheus_client
```

If not installed, metrics will be disabled with a warning.
