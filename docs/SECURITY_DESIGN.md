# Security Design for DSP-FD2

## 1. Defense in Depth Strategy

### Layer 1: Network Security
- **TLS Everywhere**: All communication encrypted with TLS 1.3+
- **Network Segmentation**: Modules run in isolated network segments
- **Ingress Control**: WAF and DDoS protection at edge

### Layer 2: Authentication & Authorization
- **JWT Validation**: Every request validated against dsp_ai_jwt service
- **API Key Management**: Rotating keys with rate limiting
- **mTLS**: Mutual TLS for service-to-service communication

### Layer 3: Module Isolation
- **Container Sandboxing**: Modules run in restricted containers
- **Resource Limits**: CPU, memory, and I/O limits per module
- **Capability Restrictions**: Minimal Linux capabilities

### Layer 4: Secret Management
- **Vault Integration**: All secrets stored in HashiCorp Vault
- **Dynamic Secrets**: Short-lived credentials with automatic rotation
- **Encryption at Rest**: All sensitive data encrypted

---

## 2. Threat Model

### A. External Threats

#### Threat: Unauthorized API Access
**Attack Vector**: Attacker attempts to access API without valid credentials
**Mitigation**:
```python
# JWT validation middleware
async def validate_jwt(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization")
    
    token = auth_header[7:]
    
    # Validate with JWT service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JWT_SERVICE_URL}/validate",
            json={
                "token": token,
                "required_claims": ["sub", "exp", "scope"],
                "validate_audience": True
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(401, "Invalid token")
    
    request.state.user_context = response.json()["claims"]
```

#### Threat: Injection Attacks
**Attack Vector**: Malicious input in request body or headers
**Mitigation**:
- Pydantic models for input validation
- SQL parameterization
- Command injection prevention

```python
# Input sanitization
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    
    @validator('model')
    def validate_model(cls, v):
        allowed_models = ["gpt-4", "gpt-3.5-turbo"]
        if v not in allowed_models:
            raise ValueError(f"Invalid model: {v}")
        return v
    
    @validator('messages')
    def validate_messages(cls, v):
        for msg in v:
            if not isinstance(msg.get("content"), str):
                raise ValueError("Invalid message content")
            # Sanitize content
            msg["content"] = sanitize_input(msg["content"])
        return v
```

---

### B. Internal Threats

#### Threat: Module Compromise
**Attack Vector**: Malicious code in dynamically loaded module
**Mitigation**:

```python
# Module validation before loading
import hashlib
import hmac

class SecureModuleLoader:
    def __init__(self, signing_key: str):
        self.signing_key = signing_key
    
    async def validate_module_signature(self, manifest: dict) -> bool:
        """Verify module code signature"""
        module_hash = manifest.get("code_signature", {}).get("hash")
        expected_signature = manifest.get("code_signature", {}).get("signature")
        
        if not module_hash or not expected_signature:
            return False
        
        # Verify signature with HMAC
        calculated_signature = hmac.new(
            self.signing_key.encode(),
            module_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_signature, expected_signature)
    
    async def load_module(self, manifest: dict) -> BaseModule:
        """Load module only if signature is valid"""
        if not await self.validate_module_signature(manifest):
            raise SecurityException("Invalid module signature")
        
        # Safe module loading with restricted imports
        safe_builtins = {
            '__builtins__': {
                'len': len, 'range': range, 'str': str,
                # Limited set of safe builtins
            }
        }
        
        # Load module in restricted environment
        module_code = await self.fetch_module_code(manifest)
        exec(module_code, safe_builtins)
```

#### Threat: Secret Exposure
**Attack Vector**: Secrets leaked through logs or responses
**Mitigation**:

```python
# Secret masking in logs
import re

class SecretMasker:
    PATTERNS = [
        (r'"api_key":\s*"[^"]*"', '"api_key": "***"'),
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+', 'Bearer ***'),
        (r'"password":\s*"[^"]*"', '"password": "***"')
    ]
    
    @classmethod
    def mask(cls, text: str) -> str:
        """Mask sensitive data in text"""
        for pattern, replacement in cls.PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text

# Custom logger
class SecureLogger:
    def __init__(self, logger):
        self.logger = logger
    
    def info(self, message: str, **kwargs):
        self.logger.info(SecretMasker.mask(message), **kwargs)
```

---

## 3. Control Tower Security

### Manifest Validation
```python
class ManifestValidator:
    def __init__(self, trusted_sources: List[str]):
        self.trusted_sources = trusted_sources
    
    async def validate_manifest(self, manifest: dict, source: str) -> bool:
        """Comprehensive manifest validation"""
        
        # 1. Source validation
        if source not in self.trusted_sources:
            raise SecurityException(f"Untrusted manifest source: {source}")
        
        # 2. Schema validation
        try:
            ManifestSchema.parse_obj(manifest)
        except ValidationError as e:
            raise SecurityException(f"Invalid manifest schema: {e}")
        
        # 3. Module type validation
        allowed_types = ["inference_openai", "rag", "data_processing"]
        if manifest.get("module_type") not in allowed_types:
            raise SecurityException("Invalid module type")
        
        # 4. Endpoint validation (prevent SSRF)
        endpoints = manifest.get("endpoints", {})
        for env, urls in endpoints.items():
            for url in urls.values():
                if not self.is_safe_url(url):
                    raise SecurityException(f"Unsafe endpoint URL: {url}")
        
        return True
    
    def is_safe_url(self, url: str) -> bool:
        """Prevent SSRF attacks"""
        parsed = urlparse(url)
        
        # Block local addresses
        blocked_hosts = [
            "localhost", "127.0.0.1", "0.0.0.0",
            "169.254.169.254"  # AWS metadata endpoint
        ]
        
        if parsed.hostname in blocked_hosts:
            return False
        
        # Only allow HTTP(S)
        if parsed.scheme not in ["http", "https"]:
            return False
        
        return True
```

---

## 4. Vault Integration

### Secret Injection Pipeline
```python
from hvac import Client

class VaultSecretManager:
    def __init__(self, vault_url: str, token: str):
        self.client = Client(url=vault_url, token=token)
    
    async def fetch_secrets(self, references: List[dict]) -> dict:
        """Fetch secrets from Vault with audit logging"""
        secrets = {}
        
        for ref in references:
            path = ref.get("source", "").replace("vault://", "")
            
            # Audit log secret access
            await self.audit_log(f"Fetching secret: {path}")
            
            try:
                # Fetch from Vault
                response = self.client.read(path)
                if response:
                    secrets[ref["name"]] = response["data"]["value"]
                    
                    # Set TTL for secret refresh
                    if "ttl" in response["data"]:
                        secrets[f"{ref['name']}_ttl"] = response["data"]["ttl"]
            except Exception as e:
                if ref.get("required", True):
                    raise SecurityException(f"Failed to fetch secret: {path}")
                else:
                    secrets[ref["name"]] = ref.get("default")
        
        return secrets
    
    async def audit_log(self, message: str):
        """Log security-relevant events"""
        # Send to SIEM
        pass
```

### Dynamic Secret Rotation
```python
class SecretRotator:
    def __init__(self, vault_manager: VaultSecretManager):
        self.vault_manager = vault_manager
        self.rotation_tasks = {}
    
    async def schedule_rotation(self, secret_name: str, ttl: int):
        """Schedule automatic secret rotation"""
        async def rotate():
            await asyncio.sleep(ttl - 60)  # Rotate 1 minute before expiry
            new_secret = await self.vault_manager.rotate_secret(secret_name)
            await self.update_modules(secret_name, new_secret)
        
        task = asyncio.create_task(rotate())
        self.rotation_tasks[secret_name] = task
```

---

## 5. Module Sandboxing

### Container Security Policy
```yaml
# security-policy.yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10000
    fsGroup: 10000
    seccompProfile:
      type: RuntimeDefault
  
  containers:
  - name: module
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
        add:
          - NET_BIND_SERVICE
      runAsNonRoot: true
      runAsUser: 10000
    
    resources:
      limits:
        cpu: "1"
        memory: "512Mi"
      requests:
        cpu: "100m"
        memory: "128Mi"
```

### Python Sandbox
```python
import resource
import sys

class ModuleSandbox:
    @staticmethod
    def apply_restrictions():
        """Apply resource and capability restrictions"""
        
        # Memory limit: 512MB
        resource.setrlimit(
            resource.RLIMIT_AS,
            (512 * 1024 * 1024, 512 * 1024 * 1024)
        )
        
        # CPU time limit: 30 seconds
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (30, 30)
        )
        
        # Disable dangerous modules
        dangerous_modules = [
            'os', 'subprocess', 'socket', 'urllib',
            '__builtins__.__import__'
        ]
        
        for module in dangerous_modules:
            if '.' in module:
                parts = module.split('.')
                obj = sys.modules.get(parts[0])
                for part in parts[1:]:
                    if obj:
                        delattr(obj, part)
            else:
                sys.modules[module] = None
```

---

## 6. Rate Limiting & DDoS Protection

```python
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked = set()
    
    async def check_rate_limit(
        self,
        client_id: str,
        limits: dict
    ) -> bool:
        """Check if request exceeds rate limits"""
        
        # Check if client is blocked
        if client_id in self.blocked:
            return False
        
        now = datetime.utcnow()
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check limits
        request_count = len(self.requests[client_id])
        
        if request_count >= limits.get("requests_per_minute", 60):
            # Block client temporarily
            self.blocked.add(client_id)
            asyncio.create_task(self.unblock_client(client_id, 300))
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True
    
    async def unblock_client(self, client_id: str, duration: int):
        """Unblock client after duration"""
        await asyncio.sleep(duration)
        self.blocked.discard(client_id)
```

---

## 7. Compliance & Audit

### Audit Logger
```python
import json
from datetime import datetime

class AuditLogger:
    def __init__(self, output_path: str):
        self.output_path = output_path
    
    async def log_request(self, request_data: dict):
        """Log all requests for compliance"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_data.get("request_id"),
            "user_id": request_data.get("user_id"),
            "action": request_data.get("action"),
            "resource": request_data.get("resource"),
            "result": request_data.get("result"),
            "ip_address": request_data.get("ip_address"),
            "user_agent": request_data.get("user_agent")
        }
        
        # Write to audit log (consider using centralized logging)
        with open(self.output_path, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
        
        # Send to SIEM
        await self.send_to_siem(audit_entry)
    
    async def send_to_siem(self, entry: dict):
        """Send audit logs to SIEM system"""
        # Implementation depends on SIEM provider
        pass
```

---

## 8. Security Monitoring

### Anomaly Detection
```python
class SecurityMonitor:
    def __init__(self):
        self.baseline = {}
        self.alerts = []
    
    async def detect_anomalies(self, metrics: dict):
        """Detect security anomalies"""
        
        # Check for unusual request patterns
        if metrics.get("requests_per_second") > self.baseline.get("max_rps", 100) * 2:
            await self.raise_alert("Possible DDoS attack detected")
        
        # Check for authentication failures
        if metrics.get("auth_failure_rate") > 0.1:  # >10% failure rate
            await self.raise_alert("High authentication failure rate")
        
        # Check for unusual module loading
        if metrics.get("new_modules_loaded") > 5:
            await self.raise_alert("Unusual module loading activity")
    
    async def raise_alert(self, message: str):
        """Raise security alert"""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "HIGH",
            "message": message
        }
        
        self.alerts.append(alert)
        
        # Send to security team
        await self.notify_security_team(alert)
```

---

## 9. Incident Response Plan

### Automated Response
```python
class IncidentResponder:
    async def handle_security_incident(self, incident_type: str):
        """Automated incident response"""
        
        if incident_type == "unauthorized_access":
            # 1. Block IP address
            # 2. Revoke potentially compromised tokens
            # 3. Alert security team
            pass
        
        elif incident_type == "module_compromise":
            # 1. Immediately unload module
            # 2. Quarantine module code
            # 3. Rollback to previous version
            # 4. Full security audit
            pass
        
        elif incident_type == "secret_exposure":
            # 1. Immediately rotate exposed secrets
            # 2. Audit all secret access
            # 3. Update affected modules
            pass
```

---

## 10. Security Checklist

- [ ] All endpoints require authentication
- [ ] JWT tokens validated on every request
- [ ] Secrets never logged or returned in responses
- [ ] Module code signatures verified
- [ ] Rate limiting applied per client
- [ ] Audit logging for all actions
- [ ] TLS 1.3+ for all connections
- [ ] Regular security scanning
- [ ] Penetration testing quarterly
- [ ] Security training for developers
