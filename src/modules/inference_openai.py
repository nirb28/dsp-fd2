"""
OpenAI-Compatible Inference Module
Handles chat completions and other OpenAI API endpoints
"""

import json
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio

from src.core.module_interface import (
    BaseModule, 
    ModuleConfig, 
    ModuleRequest, 
    ModuleResponse,
    ModuleStatus
)


class InferenceOpenAIModule(BaseModule):
    """
    Module for handling OpenAI-compatible inference requests.
    Supports multiple backend providers (OpenAI, Anthropic, local models, etc.)
    """
    
    async def initialize(self, config: ModuleConfig) -> None:
        """Initialize the inference module with backend configuration"""
        await super().initialize(config)
        
        # Validate required runtime references
        required_refs = ["api_key", "model_mapping", "rate_limits"]
        missing = [ref for ref in required_refs if ref not in config.runtime_references]
        if missing:
            raise ValueError(f"Missing required runtime references: {missing}")
        
        # Initialize provider-specific clients
        self.api_key = config.runtime_references.get("api_key")
        self.model_mapping = config.runtime_references.get("model_mapping", {})
        self.rate_limits = config.runtime_references.get("rate_limits", {})
        
        # Backend endpoint selection based on environment
        self.backend_url = config.backend_endpoints.get(
            config.environment,
            config.backend_endpoints.get("default")
        )
        
        if not self.backend_url:
            raise ValueError(f"No backend URL for environment: {config.environment}")
        
        self.status = ModuleStatus.READY
    
    async def handle_request(self, request: ModuleRequest) -> ModuleResponse:
        """
        Route OpenAI API requests to appropriate handlers
        """
        # Map paths to handlers
        handlers = {
            "/v1/chat/completions": self._handle_chat_completions,
            "/v1/completions": self._handle_completions,
            "/v1/embeddings": self._handle_embeddings,
            "/v1/models": self._handle_list_models,
        }
        
        # Strip module prefix from path if present
        path = request.path
        for prefix in ["/inference", "/inference_openai"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        
        handler = handlers.get(path)
        if not handler:
            return ModuleResponse(
                status_code=404,
                body={"error": f"Endpoint not found: {path}"}
            )
        
        try:
            return await handler(request)
        except Exception as e:
            return ModuleResponse(
                status_code=500,
                body={"error": str(e)}
            )
    
    async def _handle_chat_completions(self, request: ModuleRequest) -> ModuleResponse:
        """
        Handle /v1/chat/completions endpoint
        Supports both streaming and non-streaming responses
        """
        body = request.body
        
        # Transform request for backend if needed
        transformed_body = await self._transform_request(body)
        
        # Check if streaming is requested
        stream = body.get("stream", False)
        
        # Make request to backend
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if stream:
            # Return streaming response
            return ModuleResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                stream=self._stream_chat_response(transformed_body, headers)
            )
        else:
            # Make synchronous request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/v1/chat/completions",
                    json=transformed_body,
                    headers=headers
                )
                
                return ModuleResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=response.json()
                )
    
    async def _stream_chat_response(
        self, 
        body: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream chat completion responses using SSE format
        """
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.backend_url}/v1/chat/completions",
                json=body,
                headers=headers
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk
    
    async def _handle_completions(self, request: ModuleRequest) -> ModuleResponse:
        """Handle legacy completions endpoint"""
        # Similar implementation to chat completions
        # Can convert to chat format if backend doesn't support legacy
        body = request.body
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_url}/v1/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            return ModuleResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.json()
            )
    
    async def _handle_embeddings(self, request: ModuleRequest) -> ModuleResponse:
        """Handle embeddings generation"""
        body = request.body
        
        # Could route to RAG module if needed
        if self.config.metadata.get("use_rag_embeddings"):
            # Forward to RAG module endpoint
            rag_endpoint = self.config.runtime_references.get("rag_endpoint")
            if rag_endpoint:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{rag_endpoint}/embeddings",
                        json=body
                    )
                    return ModuleResponse(
                        status_code=response.status_code,
                        body=response.json()
                    )
        
        # Default to backend embeddings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.backend_url}/v1/embeddings",
                json=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            return ModuleResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.json()
            )
    
    async def _handle_list_models(self, request: ModuleRequest) -> ModuleResponse:
        """List available models"""
        # Return configured models from model_mapping
        models = [
            {
                "id": model_id,
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "system"
            }
            for model_id in self.model_mapping.keys()
        ]
        
        return ModuleResponse(
            status_code=200,
            body={
                "object": "list",
                "data": models
            }
        )
    
    async def _transform_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform request based on backend requirements
        E.g., map model names, adjust parameters
        """
        transformed = body.copy()
        
        # Map model names if configured
        if "model" in transformed and transformed["model"] in self.model_mapping:
            transformed["model"] = self.model_mapping[transformed["model"]]
        
        # Apply any backend-specific transformations
        backend_type = self.config.metadata.get("backend_type", "openai")
        
        if backend_type == "anthropic":
            # Convert to Anthropic format
            if "messages" in transformed:
                # Anthropic uses a slightly different message format
                pass
        elif backend_type == "cohere":
            # Convert to Cohere format
            pass
        
        return transformed
    
    async def health_check(self) -> Dict[str, Any]:
        """Check module and backend health"""
        health = await super().health_check()
        
        # Check backend connectivity
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/health",
                    timeout=5.0
                )
                health["backend_status"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health["backend_status"] = "unreachable"
        
        health["models_available"] = len(self.model_mapping)
        
        return health
    
    async def shutdown(self) -> None:
        """Cleanup resources"""
        await super().shutdown()
        # Any additional cleanup specific to inference module
