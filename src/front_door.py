"""
DSP-FD2: Dynamic Front Door Service
Routes requests to modules based on Control Tower manifests
"""

import asyncio
import hashlib
import importlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/front_door.log", mode="a")
    ]
)
logger = logging.getLogger("DSP-FD2")
logger.info(f"Starting DSP-FD2 Front Door with log level: {log_level}")

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Optional imports with fallbacks
try:
    import redis.asyncio as redis
except ImportError:
    redis = None
    print("Warning: Redis not available - caching disabled")

try:
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    print("Warning: Prometheus client not available - metrics disabled")
    # Mock prometheus classes for development
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    def generate_latest():
        return "# Prometheus metrics disabled\n"

from src.core.module_interface import BaseModule, ModuleConfig, ModuleRequest, ModuleType


# Metrics
request_counter = Counter('fd_requests_total', 'Total requests', ['project', 'module', 'environment'])
request_duration = Histogram('fd_request_duration_seconds', 'Request duration', ['project', 'module'])
manifest_cache_hits = Counter('fd_manifest_cache_hits', 'Manifest cache hits')
manifest_cache_misses = Counter('fd_manifest_cache_misses', 'Manifest cache misses')


class FrontDoorConfig(BaseModel):
    """Configuration for the Front Door service"""
    control_tower_url: str = Field(..., description="Control Tower API URL")
    vault_url: str = Field(..., description="Secrets vault URL")
    jwt_service_url: str = Field(..., description="JWT validation service URL")
    redis_url: Optional[str] = Field(default=None, description="Redis URL for caching (optional)")
    cache_ttl_seconds: int = Field(default=300, description="Manifest cache TTL")
    module_pool_size: int = Field(default=10, description="Max modules in memory")
    request_timeout: int = Field(default=30)
    environment: str = Field(default="dev")


class ModuleManager:
    """Manages module lifecycle and pooling"""
    
    def __init__(self, config: FrontDoorConfig):
        self.config = config
        self.modules: Dict[str, BaseModule] = {}
        self.module_metadata: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()
    
    async def get_or_create_module(
        self, 
        manifest: Dict[str, Any],
        runtime_refs: Dict[str, Any]
    ) -> BaseModule:
        """Get existing module or create new one"""
        module_key = self._get_module_key(manifest)
        
        async with self.lock:
            # Check if module exists and is healthy
            if module_key in self.modules:
                module = self.modules[module_key]
                health = await module.health_check()
                if health.get("status") == "ready":
                    return module
                else:
                    # Remove unhealthy module
                    await self._remove_module(module_key)
            
            # Create new module
            module = await self._create_module(manifest, runtime_refs)
            
            # Manage pool size
            if len(self.modules) >= self.config.module_pool_size:
                await self._evict_oldest_module()
            
            self.modules[module_key] = module
            self.module_metadata[module_key] = {
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow(),
                "manifest": manifest
            }
            
            return module
    
    async def _create_module(
        self,
        manifest: Dict[str, Any],
        runtime_refs: Dict[str, Any]
    ) -> BaseModule:
        """Dynamically create and initialize a module"""
        runtime = manifest.get("runtime", {})
        implementation = runtime.get("implementation")
        
        if not implementation:
            raise ValueError(f"No implementation specified in manifest")
        
        # Dynamic import
        module_path, class_name = implementation.rsplit(".", 1)
        module = importlib.import_module(module_path)
        module_class = getattr(module, class_name)
        
        # Create instance
        instance = module_class()
        
        # Initialize with config
        config = ModuleConfig(
            module_id=self._get_module_key(manifest),
            module_type=ModuleType(manifest.get("module_type")),
            version=manifest.get("manifest_version", "1.0"),
            environment=manifest.get("environment", self.config.environment),
            backend_endpoints=manifest.get("endpoints", {}).get(self.config.environment, {}),
            runtime_references=runtime_refs,
            metadata=manifest.get("metadata", {})
        )
        
        await instance.initialize(config)
        return instance
    
    def _get_module_key(self, manifest: Dict[str, Any]) -> str:
        """Generate unique key for module instance"""
        key_data = f"{manifest.get('project')}:{manifest.get('module')}:{manifest.get('environment', self.config.environment)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _remove_module(self, module_key: str):
        """Remove and shutdown a module"""
        if module_key in self.modules:
            module = self.modules[module_key]
            await module.shutdown()
            del self.modules[module_key]
            del self.module_metadata[module_key]
    
    async def _evict_oldest_module(self):
        """Evict least recently used module"""
        if not self.module_metadata:
            return
        
        oldest_key = min(
            self.module_metadata.keys(),
            key=lambda k: self.module_metadata[k]["last_used"]
        )
        await self._remove_module(oldest_key)
    
    async def shutdown_all(self):
        """Shutdown all modules"""
        for module_key in list(self.modules.keys()):
            await self._remove_module(module_key)


class FrontDoorService:
    """Main Front Door service"""
    
    def __init__(self, config: FrontDoorConfig):
        self.config = config
        self.module_manager = ModuleManager(config)
        self.redis_client = None
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize service connections"""
        # Redis for caching (optional)
        if redis is not None and hasattr(self.config, 'redis_url') and self.config.redis_url:
            try:
                logger.debug(f"Attempting Redis connection to: {self.config.redis_url}")
                self.redis_client = redis.from_url(self.config.redis_url)
                # Test the connection
                await self.redis_client.ping()
                logger.info("Redis connection successful")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        else:
            logger.info("Redis not configured - caching disabled")
            self.redis_client = None
        
        # HTTP client for external services
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.request_timeout)
        )
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
        await self.module_manager.shutdown_all()
    
    def parse_request_target(self, request: Request) -> Tuple[str, str, str]:
        """
        Extract project, module, and environment from request
        
        Supports:
        1. Path-based: /{project}/{module}/...
        2. Header-based: X-Project-Module header
        3. Subdomain-based: {project}-{module}.api.company.com
        """
        logger.debug(f"Parsing request target from URL: {request.url}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        
        # Try path-based first (recommended approach)
        path_parts = request.url.path.strip("/").split("/")
        logger.debug(f"Path parts: {path_parts}")
        
        if len(path_parts) >= 2:
            project = path_parts[0]
            module = path_parts[1]
            logger.debug(f"Found project/module from path: {project}/{module}")
        else:
            # Try header-based
            project_module = request.headers.get("X-Project-Module", "")
            if "/" in project_module:
                project, module = project_module.split("/", 1)
            else:
                # Try subdomain-based
                host = request.headers.get("host", "")
                if "-" in host:
                    subdomain = host.split(".")[0]
                    if "-" in subdomain:
                        project, module = subdomain.rsplit("-", 1)
                    else:
                        raise ValueError("Cannot determine project and module from request")
                else:
                    raise ValueError("Cannot determine project and module from request")
        
        # Get environment from header or use default
        environment = request.headers.get("X-Environment", self.config.environment)
        
        return project, module, environment
    
    async def get_manifest(
        self, 
        project: str, 
        module: str, 
        environment: str
    ) -> Dict[str, Any]:
        """Fetch manifest from Control Tower with caching"""
        cache_key = f"manifest:{project}:{module}:{environment}"
        
        # Check cache
        if self.redis_client:
            cached = await self.redis_client.get(cache_key)
            if cached:
                manifest_cache_hits.inc()
                return json.loads(cached)
        
        manifest_cache_misses.inc()
        
        # Fetch from Control Tower
        logger.debug(f"Fetching manifest for {project}/{module} from Control Tower")
        response = await self.http_client.get(
            f"{self.config.control_tower_url}/manifests/{project}/modules/{module}",
            params={"environment": environment}
        )
        logger.debug(f"Control Tower response: {response.status_code}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch manifest from Control Tower: {response.status_code}"
            )
        
        manifest = response.json()
        
        # Cache manifest
        if self.redis_client:
            await self.redis_client.setex(
                cache_key,
                self.config.cache_ttl_seconds,
                json.dumps(manifest)
            )
        
        return manifest
    
    async def resolve_runtime_references(
        self,
        references: list
    ) -> Dict[str, Any]:
        """Resolve configuration references from vault and other sources"""
        resolved = {}
        
        for ref in references:
            name = ref.get("name")
            source = ref.get("source", "")
            required = ref.get("required", True)
            default = ref.get("default")
            
            try:
                if source.startswith("vault://"):
                    # Fetch from HashiCorp Vault
                    vault_path = source.replace("vault://", "")
                    response = await self.http_client.get(
                        f"{self.config.vault_url}/v1/{vault_path}",
                        headers={"X-Vault-Token": "vault-token"}  # Should be from config
                    )
                    if response.status_code == 200:
                        data = response.json()
                        resolved[name] = data.get("data", {}).get("value")
                    elif not required and default is not None:
                        resolved[name] = default
                    else:
                        raise ValueError(f"Failed to fetch required secret: {name}")
                        
                elif source.startswith("configmap://"):
                    # Fetch from config service
                    config_path = source.replace("configmap://", "")
                    response = await self.http_client.get(
                        f"{self.config.control_tower_url}/configs/{config_path}"
                    )
                    if response.status_code == 200:
                        resolved[name] = response.json()
                    elif not required and default is not None:
                        resolved[name] = default
                    else:
                        raise ValueError(f"Failed to fetch required config: {name}")
                        
                elif source.startswith("service://"):
                    # Service discovery
                    service_path = source.replace("service://", "")
                    # Implement service discovery logic
                    resolved[name] = f"http://{service_path}.svc.cluster.local"
                    
                elif not required and default is not None:
                    resolved[name] = default
                    
            except Exception as e:
                if required:
                    raise
                elif default is not None:
                    resolved[name] = default
        
        return resolved
    
    async def validate_request_auth(
        self,
        request: Request,
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate request authentication based on manifest requirements"""
        routing = manifest.get("routing", {})
        auth = routing.get("authentication", {})
        
        if not auth.get("required", True):
            return {}
        
        # Get authorization header
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        # JWT validation
        if auth.get("jwt_validation", {}).get("enabled"):
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                
                # Validate with JWT service
                response = await self.http_client.post(
                    f"{self.config.jwt_service_url}/validate",
                    json={"token": token}
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=401, detail="Invalid token")
                
                return response.json().get("claims", {})
        
        # API key validation
        if "api_key" in auth.get("types", []):
            # Validate API key
            pass
        
        return {}
    
    async def handle_request(self, request: Request) -> Response:
        """Main request handler"""
        logger.debug(f"Handling request: {request.method} {request.url}")
        start_time = time.time()
        
        # Initialize variables for metrics
        project = "unknown"
        module = "unknown"
        
        try:
            # Parse request target
            logger.debug("Parsing request target...")
            project, module, environment = self.parse_request_target(request)
            logger.info(f"Request routed to: {project}/{module} (env: {environment})")
            
            # Increment metrics
            request_counter.labels(project=project, module=module, environment=environment).inc()
            
            # Get manifest
            manifest = await self.get_manifest(project, module, environment)
            
            # Validate authentication
            user_context = await self.validate_request_auth(request, manifest)
            
            # Resolve runtime references
            runtime_refs = await self.resolve_runtime_references(
                manifest.get("configuration_references", [])
            )
            
            # Get or create module
            module_instance = await self.module_manager.get_or_create_module(
                manifest, runtime_refs
            )
            
            # Build module request
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.json()
            
            module_request = ModuleRequest(
                request_id=request.headers.get("X-Request-ID", str(time.time())),
                method=request.method,
                path=request.url.path,
                headers=dict(request.headers),
                query_params=dict(request.query_params),
                body=body,
                user_context=user_context
            )
            
            # Handle request through module
            module_response = await module_instance.handle_request(module_request)
            
            # Build response
            if module_response.stream:
                return StreamingResponse(
                    module_response.stream,
                    status_code=module_response.status_code,
                    headers=module_response.headers
                )
            else:
                return Response(
                    content=json.dumps(module_response.body) if module_response.body else None,
                    status_code=module_response.status_code,
                    headers=module_response.headers
                )
                
        except HTTPException as he:
            logger.warning(f"HTTP exception: {he.status_code} - {he.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error handling request: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Record request duration
            duration = time.time() - start_time
            request_duration.labels(project=project, module=module).observe(duration)


# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await app.state.front_door.initialize()
    yield
    # Shutdown
    await app.state.front_door.shutdown()


# Create FastAPI app
app = FastAPI(
    title="DSPAI-FD2 Front Door",
    description="Dynamic module routing gateway",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None, redoc_url=None
)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DSPAI - Front Door",
        swagger_favicon_url="/static/fd.ico"
    )

# Initialize Front Door service
config = FrontDoorConfig(
    control_tower_url=os.getenv("CONTROL_TOWER_URL", "http://localhost:8081"),
    vault_url=os.getenv("VAULT_URL", "http://localhost:8200"),
    jwt_service_url=os.getenv("JWT_SERVICE_URL", "http://localhost:8082"),
    redis_url=os.getenv("REDIS_URL")  # Will be None if not set
)

app.state.front_door = FrontDoorService(config)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "dsp-fd2"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")


# Catch-all route for module requests
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def route_request(request: Request):
    """Route all requests to appropriate modules"""
    return await app.state.front_door.handle_request(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.front_door:app", host="0.0.0.0", port=8080, reload=True)
