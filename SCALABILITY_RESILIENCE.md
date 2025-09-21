# Scalability & Resilience Design for DSP-FD2

## 1. Horizontal Scaling Architecture

### Load Balancer Configuration
```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dsp-fd2-ingress
  annotations:
    nginx.ingress.kubernetes.io/load-balance: "least_conn"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$request_uri"
spec:
  rules:
  - host: api.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dsp-fd2-service
            port:
              number: 8080
```

### Horizontal Pod Autoscaler
```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dsp-fd2-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dsp-fd2
  minReplicas: 3
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: 1000
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

---

## 2. Failure Handling Patterns

### Circuit Breaker Implementation
```python
from enum import Enum
from datetime import datetime, timedelta
import asyncio
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to retry"""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > 
            timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Reset circuit breaker on successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage in Front Door
class ResilientFrontDoor:
    def __init__(self):
        self.control_tower_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30
        )
        self.vault_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    async def get_manifest_with_fallback(
        self,
        project: str,
        module: str,
        environment: str
    ) -> dict:
        """Get manifest with circuit breaker and fallback"""
        
        try:
            # Try to get from Control Tower with circuit breaker
            return await self.control_tower_breaker.call(
                self._fetch_from_control_tower,
                project, module, environment
            )
        except Exception as e:
            # Fallback to cache or default
            cached = await self._get_cached_manifest(project, module, environment)
            if cached:
                return cached
            
            # Last resort: embedded default manifests
            return self._get_default_manifest(module)
```

### Retry Strategy with Exponential Backoff
```python
import random
from typing import TypeVar, Callable, Optional

T = TypeVar('T')

class RetryStrategy:
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry logic"""
        
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_attempts - 1:
                    break
                
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay
```

---

## 3. High Availability Design

### Multi-Region Deployment
```python
class MultiRegionFrontDoor:
    def __init__(self, regions: List[str]):
        self.regions = regions
        self.primary_region = regions[0]
        self.health_checkers = {
            region: RegionHealthChecker(region)
            for region in regions
        }
    
    async def route_request(self, request: Request) -> Response:
        """Route request to healthy region"""
        
        # Check primary region health
        if await self.health_checkers[self.primary_region].is_healthy():
            return await self._route_to_region(request, self.primary_region)
        
        # Failover to secondary regions
        for region in self.regions[1:]:
            if await self.health_checkers[region].is_healthy():
                return await self._route_to_region(request, region)
        
        raise ServiceUnavailableException("All regions are unhealthy")

class RegionHealthChecker:
    def __init__(self, region: str):
        self.region = region
        self.healthy = True
        self.last_check = None
        self.check_interval = 10  # seconds
    
    async def is_healthy(self) -> bool:
        """Check if region is healthy with caching"""
        
        now = datetime.utcnow()
        
        if (self.last_check and 
            now - self.last_check < timedelta(seconds=self.check_interval)):
            return self.healthy
        
        try:
            # Perform health check
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{self.region}.api.company.com/health",
                    timeout=2.0
                )
                self.healthy = response.status_code == 200
        except:
            self.healthy = False
        
        self.last_check = now
        return self.healthy
```

### Database Connection Pooling
```python
from asyncpg import create_pool
from redis.asyncio import ConnectionPool

class ConnectionManager:
    def __init__(self):
        self.postgres_pool = None
        self.redis_pool = None
        self.http_clients = {}
    
    async def initialize(self):
        """Initialize connection pools"""
        
        # PostgreSQL connection pool
        self.postgres_pool = await create_pool(
            host='localhost',
            port=5432,
            user='user',
            password='password',
            database='dsp_fd2',
            min_size=10,
            max_size=50,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
        
        # Redis connection pool
        self.redis_pool = ConnectionPool(
            host='localhost',
            port=6379,
            max_connections=100,
            decode_responses=True
        )
        
        # HTTP client pool per service
        self.http_clients = {
            'control_tower': httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20
                )
            ),
            'vault': httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=10
                )
            )
        }
    
    async def get_postgres_connection(self):
        """Get connection from pool"""
        async with self.postgres_pool.acquire() as connection:
            yield connection
    
    async def get_redis_client(self):
        """Get Redis client from pool"""
        return redis.Redis(connection_pool=self.redis_pool)
```

---

## 4. Performance Optimization

### Response Caching
```python
from functools import wraps
import hashlib
import pickle

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
    
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.redis.get(key)
        if value:
            return pickle.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        await self.redis.setex(
            key,
            ttl,
            pickle.dumps(value)
        )
    
    def cached(self, prefix: str, ttl: int = None):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.cache_key(prefix, *args, **kwargs)
                
                # Check cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator

# Usage
cache_manager = CacheManager(redis_client)

@cache_manager.cached("manifest", ttl=600)
async def get_manifest(project: str, module: str, env: str) -> dict:
    # Expensive operation
    return await fetch_from_control_tower(project, module, env)
```

### Async Request Batching
```python
from collections import defaultdict
import asyncio
from typing import List, Dict, Any

class RequestBatcher:
    def __init__(self, batch_size: int = 10, batch_window: float = 0.1):
        self.batch_size = batch_size
        self.batch_window = batch_window
        self.pending_requests = defaultdict(list)
        self.batch_tasks = {}
    
    async def add_request(
        self,
        batch_key: str,
        request_data: Any
    ) -> Any:
        """Add request to batch and wait for result"""
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[batch_key].append((request_data, future))
        
        # Start batch processor if not running
        if batch_key not in self.batch_tasks:
            self.batch_tasks[batch_key] = asyncio.create_task(
                self._process_batch(batch_key)
            )
        
        # Wait for result
        return await future
    
    async def _process_batch(self, batch_key: str):
        """Process batch of requests"""
        
        while True:
            # Wait for batch window or size threshold
            await asyncio.sleep(self.batch_window)
            
            requests = self.pending_requests[batch_key]
            if not requests:
                break
            
            # Process batch
            batch_to_process = requests[:self.batch_size]
            self.pending_requests[batch_key] = requests[self.batch_size:]
            
            try:
                # Execute batch operation
                results = await self._execute_batch(
                    batch_key,
                    [req for req, _ in batch_to_process]
                )
                
                # Set results for futures
                for (_, future), result in zip(batch_to_process, results):
                    future.set_result(result)
            except Exception as e:
                # Set exception for all futures
                for _, future in batch_to_process:
                    future.set_exception(e)
        
        # Clean up task
        del self.batch_tasks[batch_key]
    
    async def _execute_batch(
        self,
        batch_key: str,
        requests: List[Any]
    ) -> List[Any]:
        """Execute batch operation - override in subclass"""
        raise NotImplementedError
```

---

## 5. Monitoring & Alerting

### Comprehensive Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge, Info
import psutil

# Business metrics
request_total = Counter(
    'fd_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'fd_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

active_requests = Gauge(
    'fd_active_requests',
    'Number of active requests'
)

module_load_time = Histogram(
    'fd_module_load_seconds',
    'Module loading time',
    ['module_type']
)

cache_hit_ratio = Gauge(
    'fd_cache_hit_ratio',
    'Cache hit ratio'
)

# System metrics
cpu_usage = Gauge('fd_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('fd_memory_usage_bytes', 'Memory usage in bytes')
open_connections = Gauge('fd_open_connections', 'Number of open connections')

class MetricsCollector:
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def collect_system_metrics(self):
        """Collect system metrics periodically"""
        while True:
            # CPU usage
            cpu_usage.set(psutil.cpu_percent())
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.used)
            
            # Open connections
            connections = len(psutil.net_connections())
            open_connections.set(connections)
            
            # Cache hit ratio
            total = self.cache_hits + self.cache_misses
            if total > 0:
                cache_hit_ratio.set(self.cache_hits / total)
            
            await asyncio.sleep(10)
    
    @contextmanager
    def track_request(self, method: str, endpoint: str):
        """Context manager to track request metrics"""
        active_requests.inc()
        start_time = time.time()
        
        try:
            yield
            status = "success"
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            request_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            active_requests.dec()
```

### Health Check System
```python
from enum import Enum
from typing import Dict, List

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    def __init__(self):
        self.checks = []
    
    def register_check(self, name: str, check_func):
        """Register a health check"""
        self.checks.append((name, check_func))
    
    async def check_health(self) -> Dict[str, Any]:
        """Run all health checks"""
        
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.checks:
            try:
                result = await check_func()
                results[name] = {
                    "status": result.get("status", HealthStatus.HEALTHY),
                    "details": result.get("details", {})
                }
                
                if result.get("status") == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.get("status") == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(e)
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }

# Health check implementations
async def check_control_tower() -> Dict[str, Any]:
    """Check Control Tower connectivity"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://control-tower/health",
                timeout=5.0
            )
            if response.status_code == 200:
                return {"status": HealthStatus.HEALTHY}
            else:
                return {"status": HealthStatus.DEGRADED}
    except:
        return {"status": HealthStatus.UNHEALTHY}

async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        # Check connection pool
        pool_size = connection_manager.postgres_pool.get_size()
        pool_free = connection_manager.postgres_pool.get_idle_size()
        
        if pool_free < pool_size * 0.1:  # Less than 10% free
            return {
                "status": HealthStatus.DEGRADED,
                "details": {
                    "pool_size": pool_size,
                    "pool_free": pool_free
                }
            }
        return {"status": HealthStatus.HEALTHY}
    except:
        return {"status": HealthStatus.UNHEALTHY}
```

---

## 6. Graceful Degradation

```python
class GracefulDegradation:
    def __init__(self):
        self.feature_flags = {
            "use_cache": True,
            "validate_manifests": True,
            "collect_metrics": True,
            "rate_limiting": True
        }
        self.degradation_mode = False
    
    async def handle_with_degradation(
        self,
        request: Request
    ) -> Response:
        """Handle request with graceful degradation"""
        
        # Check system load
        if await self._is_system_overloaded():
            self.enable_degradation_mode()
        
        if self.degradation_mode:
            # Disable non-essential features
            self.feature_flags["collect_metrics"] = False
            self.feature_flags["validate_manifests"] = False
            
            # Return cached responses if available
            cached = await self._get_cached_response(request)
            if cached:
                return cached
            
            # Limit complex operations
            if self._is_complex_request(request):
                return Response(
                    status_code=503,
                    content={
                        "error": "Service temporarily limited",
                        "retry_after": 60
                    }
                )
        
        # Normal processing
        return await self._process_request(request)
    
    async def _is_system_overloaded(self) -> bool:
        """Check if system is overloaded"""
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        
        return cpu > 90 or memory > 90
    
    def enable_degradation_mode(self):
        """Enable degradation mode"""
        self.degradation_mode = True
        # Schedule recovery check
        asyncio.create_task(self._check_recovery())
    
    async def _check_recovery(self):
        """Check if system has recovered"""
        await asyncio.sleep(60)
        
        if not await self._is_system_overloaded():
            self.degradation_mode = False
            # Re-enable features
            self.feature_flags = {k: True for k in self.feature_flags}
```

---

## 7. Deployment Strategy

### Blue-Green Deployment
```bash
#!/bin/bash
# deploy.sh - Blue-Green deployment script

# Current production environment
CURRENT_ENV=$(kubectl get service dsp-fd2 -o jsonpath='{.spec.selector.env}')
if [ "$CURRENT_ENV" == "blue" ]; then
    NEW_ENV="green"
else
    NEW_ENV="blue"
fi

echo "Deploying to $NEW_ENV environment..."

# Deploy new version
kubectl apply -f kubernetes/deployment-$NEW_ENV.yaml

# Wait for rollout
kubectl rollout status deployment/dsp-fd2-$NEW_ENV

# Run smoke tests
python scripts/smoke_test.py --env $NEW_ENV

if [ $? -eq 0 ]; then
    echo "Smoke tests passed, switching traffic..."
    
    # Switch traffic
    kubectl patch service dsp-fd2 -p '{"spec":{"selector":{"env":"'$NEW_ENV'"}}}'
    
    # Monitor for 5 minutes
    sleep 300
    
    # Check error rate
    ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query?query=rate(fd_requests_total{status="error"}[5m]) | jq '.data.result[0].value[1]')
    
    if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
        echo "High error rate detected, rolling back..."
        kubectl patch service dsp-fd2 -p '{"spec":{"selector":{"env":"'$CURRENT_ENV'"}}}'
        exit 1
    fi
    
    echo "Deployment successful!"
    
    # Clean up old deployment after 24 hours
    echo "kubectl delete deployment dsp-fd2-$CURRENT_ENV" | at now + 24 hours
else
    echo "Smoke tests failed, aborting deployment"
    kubectl delete deployment dsp-fd2-$NEW_ENV
    exit 1
fi
```

### Canary Deployment
```yaml
# kubernetes/canary-deployment.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: dsp-fd2
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dsp-fd2
  progressDeadlineSeconds: 600
  service:
    port: 8080
    targetPort: 8080
    gateways:
    - public-gateway.istio-system.svc.cluster.local
    hosts:
    - api.company.com
  analysis:
    interval: 30s
    threshold: 10
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: load-test
      url: http://flagger-loadtester.test/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://api.company.com/"
```

---

## Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Request Latency (P50) | < 50ms | - | 🟡 |
| Request Latency (P95) | < 200ms | - | 🟡 |
| Request Latency (P99) | < 500ms | - | 🟡 |
| Throughput | > 10,000 RPS | - | 🟡 |
| Error Rate | < 0.1% | - | 🟡 |
| Availability | 99.95% | - | 🟡 |
| Module Load Time | < 1s | - | 🟡 |
| Cache Hit Rate | > 80% | - | 🟡 |

## Capacity Planning

```python
def calculate_capacity(
    avg_rps: float,
    peak_multiplier: float = 3.0,
    growth_rate: float = 1.5,
    months_ahead: int = 12
) -> dict:
    """Calculate required capacity"""
    
    # Current requirements
    peak_rps = avg_rps * peak_multiplier
    
    # Future requirements
    future_rps = peak_rps * (growth_rate ** (months_ahead / 12))
    
    # Instance requirements (assuming 1000 RPS per instance)
    instances_needed = math.ceil(future_rps / 1000)
    
    # Add redundancy (N+2)
    total_instances = instances_needed + 2
    
    # Resource requirements per instance
    cpu_per_instance = 2  # cores
    memory_per_instance = 4  # GB
    
    return {
        "current_avg_rps": avg_rps,
        "peak_rps": peak_rps,
        "future_peak_rps": future_rps,
        "instances_required": total_instances,
        "total_cpu_cores": total_instances * cpu_per_instance,
        "total_memory_gb": total_instances * memory_per_instance,
        "estimated_monthly_cost": total_instances * 100  # $100 per instance
    }
```
