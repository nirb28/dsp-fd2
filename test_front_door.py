"""
Test script for Front Door Service
Tests both APISIX and direct routing modes
"""

import asyncio
import json
import httpx

# Configuration
FRONT_DOOR_URL = "http://localhost:8080"
CONTROL_TOWER_URL = "http://localhost:8081"
CONTROL_TOWER_SECRET = "dspsa_p@ssword"


async def test_health_check():
    """Test health check endpoint"""
    print("\n1. Testing Health Check...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FRONT_DOOR_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Service healthy")
                print(f"  - Service: {data.get('service')}")
                print(f"  - Status: {data.get('status')}")
                
                # Show routing modes
                routing_modes = data.get("routing_modes", {})
                if routing_modes:
                    print("\n  Routing Modes:")
                    for mode, projects in routing_modes.items():
                        print(f"    - {mode}: {len(projects)} projects")
                        for project in projects[:3]:  # Show first 3 projects
                            print(f"      • {project}")
                
                # Show APISIX status
                if "apisix" in data:
                    print(f"\n  APISIX Status: {data['apisix'].get('status', 'unknown')}")
                
                # Show module status
                if "modules" in data:
                    print(f"\n  Loaded Modules: {data['modules'].get('loaded', 0)}/{data['modules'].get('pool_size', 0)}")
                
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_sync_manifests():
    """Test manifest synchronization"""
    print("\n2. Testing Manifest Sync...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{FRONT_DOOR_URL}/admin/sync")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Manifests synced successfully")
                
                projects = data.get("projects", {})
                for mode, project_list in projects.items():
                    if project_list:
                        print(f"  - {mode} routing: {len(project_list)} projects")
                
                return True
            else:
                print(f"✗ Sync failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_list_projects():
    """Test listing configured projects"""
    print("\n3. Listing Configured Projects...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FRONT_DOOR_URL}/admin/projects")
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get("projects", {})
                
                print(f"✓ Found {data.get('total', 0)} configured projects")
                
                # Group by routing mode
                apisix_projects = []
                direct_projects = []
                
                for project_id, info in projects.items():
                    if info.get("routing_mode") == "apisix":
                        apisix_projects.append(project_id)
                    elif info.get("routing_mode") == "direct":
                        direct_projects.append(project_id)
                
                if apisix_projects:
                    print(f"\n  APISIX Routing ({len(apisix_projects)} projects):")
                    for project in apisix_projects[:5]:  # Show first 5
                        print(f"    • {project}")
                
                if direct_projects:
                    print(f"\n  Direct Routing ({len(direct_projects)} projects):")
                    for project in direct_projects[:5]:  # Show first 5
                        print(f"    • {project}")
                
                return True
            else:
                print(f"✗ Failed to list projects: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_configure_project(project_id: str):
    """Test configuring a specific project"""
    print(f"\n4. Testing Project Configuration for: {project_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{FRONT_DOOR_URL}/admin/configure/{project_id}")
            
            if response.status_code == 200:
                data = response.json()
                routing_mode = data.get("routing_mode")
                status = data.get("status")
                
                if status == "configured":
                    print(f"✓ Project configured successfully")
                    print(f"  - Project ID: {data.get('project_id')}")
                    print(f"  - Routing Mode: {routing_mode}")
                    
                    # If APISIX routing, show resources
                    if routing_mode == "apisix":
                        try:
                            resources_response = await client.get(
                                f"{FRONT_DOOR_URL}/admin/apisix/projects/{project_id}/resources"
                            )
                            if resources_response.status_code == 200:
                                resources = resources_response.json()
                                summary = resources.get("summary", {})
                                print(f"\n  APISIX Resources:")
                                print(f"    - Routes: {summary.get('total_routes', 0)}")
                                print(f"    - Services: {summary.get('total_services', 0)}")
                                print(f"    - Upstreams: {summary.get('total_upstreams', 0)}")
                                print(f"    - Consumers: {summary.get('total_consumers', 0)}")
                        except:
                            pass
                    
                    return True
                else:
                    print(f"✗ Project configuration failed")
                    return False
            else:
                print(f"✗ Configure failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_request_routing(project_id: str, path: str = "/test"):
    """Test actual request routing"""
    print(f"\n5. Testing Request Routing for: {project_id}{path}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Make a test request
            response = await client.get(f"{FRONT_DOOR_URL}/{project_id}{path}")
            
            print(f"  - Status Code: {response.status_code}")
            
            if response.status_code in [200, 401, 404]:
                # Expected status codes
                if response.status_code == 200:
                    print(f"✓ Request routed successfully")
                elif response.status_code == 401:
                    print(f"✓ Request routed (authentication required)")
                elif response.status_code == 404:
                    print(f"✓ Request routed (endpoint not found)")
                
                # Show response headers to identify routing
                if "X-Kong-Upstream-Latency" in response.headers or "X-APISIX" in response.headers:
                    print(f"  - Routed through: APISIX Gateway")
                else:
                    print(f"  - Routed through: Direct Module")
                
                return True
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def create_test_manifests():
    """Create test manifests with different routing configurations"""
    print("\n0. Creating Test Manifests...")
    
    headers = {"X-DSPAI-Client-Secret": CONTROL_TOWER_SECRET}
    
    # Manifest with APISIX
    manifest_with_apisix = {
        "manifest": {
            "project_id": "test-apisix-routing",
            "project_name": "Test APISIX Routing",
            "version": "1.0.0",
            "modules": [
                {
                    "module_type": "api_gateway",
                    "name": "test-apisix-gateway",
                    "config": {
                        "routes": [
                            {
                                "name": "test-route",
                                "uri": "/test",
                                "methods": ["GET"]
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    # Manifest without APISIX (direct routing)
    manifest_direct = {
        "manifest": {
            "project_id": "test-direct-routing",
            "project_name": "Test Direct Routing",
            "version": "1.0.0",
            "modules": [
                {
                    "module_type": "inference_endpoint",
                    "name": "test-llm",
                    "config": {
                        "model": "test-model",
                        "endpoint": "http://localhost:8000"
                    }
                }
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Create APISIX manifest
        try:
            response = await client.post(
                f"{CONTROL_TOWER_URL}/manifests",
                json=manifest_with_apisix,
                headers=headers
            )
            if response.status_code in [201, 409]:
                print("✓ APISIX test manifest created/exists")
        except Exception as e:
            print(f"  Warning: Could not create APISIX manifest: {e}")
        
        # Create direct routing manifest
        try:
            response = await client.post(
                f"{CONTROL_TOWER_URL}/manifests",
                json=manifest_direct,
                headers=headers
            )
            if response.status_code in [201, 409]:
                print("✓ Direct routing test manifest created/exists")
        except Exception as e:
            print(f"  Warning: Could not create direct manifest: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Unified Front Door Test Suite")
    print("=" * 60)
    
    # Create test manifests first
    await create_test_manifests()
    
    tests = [
        ("Health Check", test_health_check, None),
        ("Sync Manifests", test_sync_manifests, None),
        ("List Projects", test_list_projects, None),
        ("Configure APISIX Project", test_configure_project, "test-apisix-routing"),
        ("Configure Direct Project", test_configure_project, "test-direct-routing"),
        ("Test APISIX Routing", test_request_routing, "test-apisix-routing"),
        ("Test Direct Routing", test_request_routing, "test-direct-routing"),
    ]
    
    results = []
    for test_info in tests:
        if len(test_info) == 3:
            test_name, test_func, arg = test_info
            try:
                if arg is None:
                    result = await test_func()
                else:
                    result = await test_func(arg)
                results.append((test_name, result))
            except Exception as e:
                print(f"✗ Test '{test_name}' failed with exception: {e}")
                results.append((test_name, False))
        
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Unified routing is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
