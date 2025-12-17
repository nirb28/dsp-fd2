"""
Test script for Health Check and Metrics services
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from observability.health_service import (
    HealthCheckService, 
    HealthCheckConfig, 
    HealthCheckTargetConfig,
    HealthStatus,
    HealthCheckResult
)
from observability.metrics_service import (
    MetricsService,
    MetricsConfig,
    MetricDefinition,
    MetricType
)


class TestHealthCheckService:
    """Tests for HealthCheckService"""
    
    @pytest.fixture
    def health_config(self):
        """Create a test health check configuration"""
        return HealthCheckConfig(
            enabled=True,
            endpoint_path="/health",
            targets=[
                HealthCheckTargetConfig(
                    name="httpbin-get",
                    url="https://httpbin.org/get",
                    method="GET",
                    timeout_seconds=10,
                    expected_status_codes=[200],
                    critical=True,
                ),
                HealthCheckTargetConfig(
                    name="httpbin-status-200",
                    url="https://httpbin.org/status/200",
                    method="GET",
                    timeout_seconds=10,
                    expected_status_codes=[200],
                    critical=True,
                ),
            ],
            parallel_checks=True,
            include_details=True,
        )
    
    @pytest.fixture
    def health_service(self, health_config):
        """Create a health check service"""
        return HealthCheckService(health_config)
    
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self, health_service):
        """Test service initialization and shutdown"""
        await health_service.initialize()
        assert health_service.http_client is not None
        await health_service.shutdown()
        assert health_service.http_client is None
    
    @pytest.mark.asyncio
    async def test_liveness_check(self, health_service):
        """Test liveness check returns healthy"""
        await health_service.initialize()
        try:
            result = await health_service.liveness_check()
            assert result["status"] == "healthy"
            assert "timestamp" in result
        finally:
            await health_service.shutdown()
    
    @pytest.mark.asyncio
    async def test_check_all_no_targets(self):
        """Test check_all with no targets configured"""
        config = HealthCheckConfig(enabled=True, targets=[])
        service = HealthCheckService(config)
        await service.initialize()
        try:
            result = await service.check_all()
            assert result["status"] == "healthy"
            assert "No health check targets configured" in result.get("message", "")
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_disabled_health_check(self):
        """Test that disabled health check returns healthy"""
        config = HealthCheckConfig(enabled=False)
        service = HealthCheckService(config)
        result = await service.check_all()
        assert result["status"] == "healthy"
        assert "Health checks disabled" in result.get("message", "")
    
    def test_json_path_extraction(self, health_service):
        """Test JSON path extraction"""
        data = {
            "status": "healthy",
            "nested": {"value": 42},
            "array": [{"name": "first"}, {"name": "second"}]
        }
        
        assert health_service._extract_json_path(data, "$.status") == "healthy"
        assert health_service._extract_json_path(data, "$.nested.value") == 42
        assert health_service._extract_json_path(data, "$.array[0].name") == "first"
        assert health_service._extract_json_path(data, "$.nonexistent") is None
    
    def test_from_manifest_config(self):
        """Test creating service from manifest config dict"""
        manifest_config = {
            "enabled": True,
            "endpoint_path": "/health",
            "targets": [
                {
                    "name": "test-service",
                    "url": "http://localhost:8080/health",
                    "method": "GET",
                    "expected_status_codes": [200],
                    "critical": True,
                }
            ],
            "parallel_checks": True,
            "include_details": True,
        }
        
        service = HealthCheckService.from_manifest_config(manifest_config)
        assert service.config.enabled is True
        assert len(service.config.targets) == 1
        assert service.config.targets[0].name == "test-service"


class TestMetricsService:
    """Tests for MetricsService"""
    
    @pytest.fixture
    def metrics_config(self):
        """Create a test metrics configuration"""
        return MetricsConfig(
            enabled=True,
            endpoint_path="/metrics",
            namespace="test_app",
            default_labels={"environment": "test"},
            enable_default_metrics=True,
            default_metrics=["request_count", "request_latency_seconds"],
            custom_metrics=[
                MetricDefinition(
                    name="custom_counter",
                    type=MetricType.COUNTER,
                    description="A custom counter",
                    labels=["label1"],
                ),
                MetricDefinition(
                    name="custom_gauge",
                    type=MetricType.GAUGE,
                    description="A custom gauge",
                    labels=["label1"],
                ),
            ],
        )
    
    @pytest.fixture
    def metrics_service(self, metrics_config):
        """Create a metrics service"""
        return MetricsService(metrics_config)
    
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self, metrics_service):
        """Test service initialization and shutdown"""
        await metrics_service.initialize()
        assert metrics_service._initialized is True
        await metrics_service.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_metrics_output(self, metrics_service):
        """Test getting metrics output"""
        await metrics_service.initialize()
        try:
            output = metrics_service.get_metrics_output()
            assert isinstance(output, bytes)
            # Should contain some metric data
            assert len(output) > 0
        finally:
            await metrics_service.shutdown()
    
    @pytest.mark.asyncio
    async def test_inc_counter(self, metrics_service):
        """Test incrementing a counter"""
        await metrics_service.initialize()
        try:
            # This should not raise an error
            metrics_service.inc_counter("request_count", method="GET", endpoint="/test", status_code="200")
        finally:
            await metrics_service.shutdown()
    
    @pytest.mark.asyncio
    async def test_observe_histogram(self, metrics_service):
        """Test observing a histogram"""
        await metrics_service.initialize()
        try:
            # This should not raise an error
            metrics_service.observe_histogram("request_latency_seconds", 0.5, method="GET", endpoint="/test")
        finally:
            await metrics_service.shutdown()
    
    @pytest.mark.asyncio
    async def test_record_request(self, metrics_service):
        """Test recording a request"""
        await metrics_service.initialize()
        try:
            # This should not raise an error
            metrics_service.record_request(
                method="POST",
                endpoint="/api/query",
                status_code=200,
                latency_seconds=0.123,
                request_size=1024,
                response_size=2048
            )
        finally:
            await metrics_service.shutdown()
    
    def test_from_manifest_config(self):
        """Test creating service from manifest config dict"""
        manifest_config = {
            "enabled": True,
            "endpoint_path": "/metrics",
            "namespace": "my_app",
            "default_labels": {"env": "prod"},
            "enable_default_metrics": True,
            "custom_metrics": [
                {
                    "name": "my_counter",
                    "type": "counter",
                    "description": "My custom counter",
                    "labels": ["status"],
                }
            ],
        }
        
        service = MetricsService.from_manifest_config(manifest_config)
        assert service.config.enabled is True
        assert service.config.namespace == "my_app"
        assert len(service.config.custom_metrics) == 1
        assert service.config.custom_metrics[0].name == "my_counter"
    
    def test_get_metrics_info(self, metrics_service):
        """Test getting metrics info"""
        info = metrics_service.get_metrics_info()
        assert info["enabled"] is True
        assert info["namespace"] == "test_app"
        assert info["endpoint_path"] == "/metrics"


class TestHealthCheckAssertions:
    """Tests for health check response assertions"""
    
    @pytest.fixture
    def service(self):
        """Create a basic health check service"""
        config = HealthCheckConfig(enabled=True, targets=[])
        return HealthCheckService(config)
    
    def test_status_code_assertion(self, service):
        """Test status code assertion logic"""
        target = HealthCheckTargetConfig(
            name="test",
            url="http://test",
            expected_status_codes=[200, 201],
        )
        # 200 should pass
        assert 200 in target.expected_status_codes
        # 404 should fail
        assert 404 not in target.expected_status_codes
    
    def test_json_path_nested(self, service):
        """Test nested JSON path extraction"""
        data = {
            "data": {
                "health": {
                    "status": "ok",
                    "checks": [
                        {"name": "db", "status": "up"},
                        {"name": "cache", "status": "up"}
                    ]
                }
            }
        }
        
        assert service._extract_json_path(data, "$.data.health.status") == "ok"
        assert service._extract_json_path(data, "$.data.health.checks[0].name") == "db"
        assert service._extract_json_path(data, "$.data.health.checks[1].status") == "up"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
