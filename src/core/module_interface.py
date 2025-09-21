"""
Module Interface Contract v1.0
All modules must implement this interface for the Front Door to load and execute them.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from enum import Enum
import httpx


class ModuleType(str, Enum):
    """Supported module types"""
    INFERENCE_OPENAI = "inference_openai"
    INFERENCE_GENERIC = "inference_generic"
    RAG = "rag"
    DATA_PROCESSING = "data_processing"
    EVALUATION = "evaluation"
    TRAINING = "training"


class ModuleStatus(str, Enum):
    """Module lifecycle status"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class ModuleConfig(BaseModel):
    """Configuration passed to module during initialization"""
    module_id: str = Field(..., description="Unique module instance ID")
    module_type: ModuleType
    version: str = Field(default="1.0.0")
    environment: str = Field(..., description="dev, staging, prod")
    backend_endpoints: Dict[str, str] = Field(..., description="Backend service URLs")
    runtime_references: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resolved secrets and configs from vault"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModuleRequest(BaseModel):
    """Standard request wrapper for module invocation"""
    request_id: str = Field(..., description="Unique request tracking ID")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path within module")
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    user_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="JWT claims, user permissions, etc."
    )


class ModuleResponse(BaseModel):
    """Standard response from module"""
    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    stream: Optional[AsyncGenerator[bytes, None]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseModule(ABC):
    """
    Base class that all modules must inherit from.
    Supports both sync and async operations.
    """
    
    def __init__(self):
        self.config: Optional[ModuleConfig] = None
        self.status: ModuleStatus = ModuleStatus.UNINITIALIZED
        self.http_client: Optional[httpx.AsyncClient] = None
    
    @abstractmethod
    async def initialize(self, config: ModuleConfig) -> None:
        """
        Initialize the module with configuration.
        Called once when module is loaded.
        
        Args:
            config: Module configuration including secrets
        
        Raises:
            Exception: If initialization fails
        """
        self.config = config
        self.status = ModuleStatus.INITIALIZING
        
        # Initialize HTTP client for backend calls
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=100)
        )
    
    @abstractmethod
    async def handle_request(self, request: ModuleRequest) -> ModuleResponse:
        """
        Process an incoming request.
        
        Args:
            request: Wrapped request from the Front Door
            
        Returns:
            ModuleResponse: Response to be sent back to client
            
        Raises:
            Exception: If request processing fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the module.
        
        Returns:
            Dict containing health status and metadata
        """
        return {
            "status": self.status.value,
            "module_id": self.config.module_id if self.config else None,
            "version": self.config.version if self.config else None
        }
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the module.
        Clean up resources, close connections, etc.
        """
        self.status = ModuleStatus.SHUTTING_DOWN
        if self.http_client:
            await self.http_client.aclose()
    
    async def validate_request(self, request: ModuleRequest) -> Optional[str]:
        """
        Optional request validation.
        
        Returns:
            Error message if validation fails, None otherwise
        """
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get module metrics for monitoring.
        
        Returns:
            Dict of metric name to value
        """
        return {}


class StreamingModule(BaseModule):
    """
    Extended base for modules that support streaming responses.
    """
    
    @abstractmethod
    async def handle_streaming_request(
        self, 
        request: ModuleRequest
    ) -> AsyncGenerator[bytes, None]:
        """
        Handle requests that require streaming responses.
        
        Args:
            request: Incoming request
            
        Yields:
            Chunks of response data
        """
        pass
