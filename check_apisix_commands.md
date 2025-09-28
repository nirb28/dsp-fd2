# APISIX Diagnostic Commands

## 1. Check Available Plugins
```bash
# List all available plugins
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9180/apisix/admin/plugins/list

# Check specific plugin schema (if it exists)
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9180/apisix/admin/schema/plugins/ai-prompt-template
```

## 2. Check Configured Routes
```bash
# List all routes
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9180/apisix/admin/routes

# Get specific route by ID
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9180/apisix/admin/routes/1
```

## 3. Check Upstreams
```bash
# List all upstreams
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9180/apisix/admin/upstreams
```

## 4. Test Direct Gateway Access
```bash
# Test basic gateway
curl http://localhost:9080/

# Test specific route
curl -X POST http://localhost:9080/v1/inference/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "max_tokens": 10}'
```

## 5. Check APISIX Logs
```bash
# If using Docker
docker logs apisix
docker logs apisix-dashboard

# If using systemd
sudo journalctl -u apisix -f

# Direct log files
tail -f /usr/local/apisix/logs/error.log
tail -f /usr/local/apisix/logs/access.log
```

## 6. Common Issues and Solutions

### Issue: ai-prompt-template plugin not found
**Solutions:**
1. **Use proxy-rewrite + serverless-pre-function instead**
2. **Install the plugin** (if available in APISIX ecosystem)
3. **Create custom plugin**
4. **Direct proxy approach** (remove ai-prompt-template, just proxy to Groq)

### Issue: 404 on routes
**Check:**
1. Route URI patterns match your requests
2. HTTP methods are correct
3. Upstream is healthy
4. Plugin configuration is valid

### Issue: Upstream connection failed
**Check:**
1. Network connectivity to api.groq.com
2. SSL/TLS configuration
3. Firewall settings
4. DNS resolution
