"""
APISIX Data Models
Pydantic models for APISIX resources
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class APISIXPlugin(BaseModel):
    """APISIX plugin configuration"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    priority: Optional[int] = None


class APISIXRoute(BaseModel):
    """APISIX route configuration"""
    id: Optional[str] = None
    name: str
    uri: str
    methods: List[str] = Field(default_factory=lambda: ["GET", "POST"])
    upstream: Optional[Dict[str, Any]] = None  # Inline upstream configuration
    upstream_id: Optional[str] = None
    service_id: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    host: Optional[str] = None
    priority: int = 0
    vars: Optional[List[List]] = None
    enable_websocket: bool = False
    desc: Optional[str] = None


class APISIXUpstream(BaseModel):
    """APISIX upstream configuration"""
    id: Optional[str] = None
    name: str
    type: str = "roundrobin"
    nodes: Dict[str, int]
    timeout: Dict[str, int] = Field(
        default_factory=lambda: {"connect": 30, "send": 30, "read": 30}
    )
    retries: int = 1
    retry_timeout: int = 0
    pass_host: str = "pass"
    scheme: str = Field(default="https")
    hash_on: Optional[str] = None


class APISIXService(BaseModel):
    """APISIX service configuration"""
    id: Optional[str] = None
    name: str
    desc: Optional[str] = None
    upstream_id: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    enable_websocket: bool = False


class APISIXConsumer(BaseModel):
    """APISIX consumer configuration"""
    username: str
    desc: Optional[str] = None
    plugins: Dict[str, Any] = Field(default_factory=dict)
    group_id: Optional[str] = None
