# SAS2Py Langfuse Integration Setup

## Overview

The sas2py manifest in Control Tower now includes **Langfuse observability** for tracking LLM requests during SAS to Python code conversion.

## What Was Added

### 1. Monitoring Module
```json
{
  "module_type": "monitoring",
  "name": "langfuse-observability",
  "config": {
    "provider": "langfuse",
    "host": "${environments.${environment}.urls.langfuse_host}",
    "public_key": "${environments.${environment}.secrets.langfuse_public_key}",
    "secret_key": "${environments.${environment}.secrets.langfuse_secret_key}",
    "project_name": "sas2py",
    "sample_rate": 1.0
  }
}
```

### 2. Global APISIX Plugins
Added to `apisix-convert-route` module:
- **request-id**: UUID tracking for trace correlation
- **prometheus**: Metrics collection
- **http-logger**: Sends traces to Langfuse

### 3. Environment Variables
Added to all environments (development, staging, production):
```json
"secrets": {
  "langfuse_public_key": "${LANGFUSE_PUBLIC_KEY}",
  "langfuse_secret_key": "${LANGFUSE_SECRET_KEY}"
},
"urls": {
  "langfuse_host": "https://cloud.langfuse.com"
}
```

## Setup Instructions

### Step 1: Get Langfuse Keys

1. Go to https://cloud.langfuse.com
2. Sign up or log in
3. Create a project named "sas2py"
4. Copy your public key (`pk-lf-...`) and secret key (`sk-lf-...`)

### Step 2: Set Environment Variables

```bash
# On Control Tower server
export LANGFUSE_PUBLIC_KEY="pk-lf-your-public-key"
export LANGFUSE_SECRET_KEY="sk-lf-your-secret-key"

# Or add to .env file
echo "LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key" >> .env
echo "LANGFUSE_SECRET_KEY=sk-lf-your-secret-key" >> .env
```

### Step 3: Restart Control Tower

```bash
# Restart to load new environment variables
docker-compose restart control-tower
# or
python app.py
```

### Step 4: Sync APISIX Configuration

The Front Door will automatically sync the updated manifest:

```bash
# Test the sync
curl -X POST http://localhost:8080/admin/sync

# Or run the test script
python test_sas2py_manifest.py
```

### Step 5: Verify Langfuse Integration

1. Send a test request through APISIX:
```bash
curl -X POST http://localhost:9080/sas2py/convert \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instant",
    "messages": [
      {"role": "user", "content": "Convert this SAS code to Python: data test; set sashelp.class; run;"}
    ]
  }'
```

2. Check Langfuse dashboard:
   - Go to https://cloud.langfuse.com
   - Select "sas2py" project
   - View traces in the dashboard

## What Gets Tracked

Langfuse will capture:
- ✅ **Request ID**: Unique identifier for each request
- ✅ **Request Body**: SAS code input and LLM prompt
- ✅ **Response Body**: Generated Python code
- ✅ **Latency**: Time taken for conversion
- ✅ **Model**: LLM model used (llama-3.1-8b-instant)
- ✅ **Metadata**: Service, environment, version
- ✅ **Status**: Success/failure of requests

## Manifest Location

The sas2py manifest is stored in **Control Tower**:
```
dsp-ai-control-tower/manifests/sas2py.json
```

**Important**: Never store manifests in Front Door. Front Door fetches them from Control Tower via API.

## Testing

Run the test script to verify everything works:

```bash
cd dsp-fd2
python test_sas2py_manifest.py
```

Expected output:
```
✓ Manifest retrieved: 6 modules
✓ Direct APISIX configuration complete
  Routes created: 2
  Upstreams created: 1
✓ Langfuse observability enabled
```

## Troubleshooting

### No traces in Langfuse?

1. **Check environment variables**:
```bash
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY
```

2. **Check Control Tower logs**:
```bash
docker logs control-tower | grep langfuse
```

3. **Verify manifest resolution**:
```bash
curl "http://localhost:8000/manifests/sas2py?resolve_env=true" | jq '.modules[] | select(.name=="langfuse-observability")'
```

4. **Check APISIX logs**:
```bash
docker logs apisix | grep http-logger
```

### Authentication errors?

Make sure your Langfuse keys are correct:
- Public key starts with `pk-lf-`
- Secret key starts with `sk-lf-`
- Keys are properly base64 encoded in the auth header

### High latency?

Adjust batching settings in the manifest:
```json
"batch_max_size": 500,
"inactive_timeout": 10,
"include_resp_body": false
```

## Configuration Options

### Sampling Rate

Control what percentage of requests are traced:

```json
"sample_rate": 0.1  // 10% sampling for high-volume scenarios
```

### Metadata

Add custom metadata for filtering:

```json
"metadata": {
  "service": "sas2py",
  "environment": "production",
  "version": "1.0.0",
  "team": "data-migration",
  "cost_center": "analytics"
}
```

### Self-Hosted Langfuse

To use a self-hosted Langfuse instance:

```json
"urls": {
  "langfuse_host": "http://langfuse.internal:3000"
}
```

## Benefits

With Langfuse integration, you can:

1. **Track Usage**: See how many conversions are performed
2. **Monitor Performance**: Identify slow requests
3. **Debug Issues**: Inspect failed conversions
4. **Analyze Costs**: Track token usage and costs
5. **Improve Quality**: Review conversion quality over time
6. **Optimize Prompts**: Test different prompts and compare results

## Resources

- **Langfuse Docs**: https://langfuse.com/docs
- **Control Tower Manifest**: `dsp-ai-control-tower/manifests/sas2py.json`
- **Test Script**: `dsp-fd2/test_sas2py_manifest.py`
- **APISIX Integration**: [docs/README_APISIX.md](README_APISIX.md)
- **Langfuse Quick Start**: [docs/LANGFUSE_QUICK_START.md](LANGFUSE_QUICK_START.md)
