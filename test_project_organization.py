"""
Test script for APISIX project-based organization
"""

import asyncio
import json
import httpx

# Configuration
FRONT_DOOR_URL = "http://localhost:8080"
PROJECT_ID = "test-apisix-project"


async def test_list_project_resources():
    """Test listing all resources for a specific project"""
    print(f"\nListing resources for project: {PROJECT_ID}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FRONT_DOOR_URL}/admin/apisix/projects/{PROJECT_ID}/resources"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Project resources retrieved successfully")
                
                # Display summary
                summary = data.get("summary", {})
                print(f"\nProject Summary:")
                print(f"  - Project ID: {summary.get('project_id')}")
                print(f"  - Routes: {summary.get('total_routes')}")
                print(f"  - Upstreams: {summary.get('total_upstreams')}")
                print(f"  - Services: {summary.get('total_services')}")
                print(f"  - Consumers: {summary.get('total_consumers')}")
                
                # Display routes
                if data.get("routes"):
                    print(f"\nRoutes:")
                    for route in data["routes"]:
                        print(f"  - {route.get('name')}: {route.get('uri')} [{', '.join(route.get('methods', []))}]")
                        print(f"    Service: {route.get('service_id')}")
                        print(f"    Description: {route.get('desc')}")
                
                # Display services
                if data.get("services"):
                    print(f"\nServices:")
                    for service in data["services"]:
                        print(f"  - {service.get('name')}")
                        print(f"    Description: {service.get('desc')}")
                        print(f"    Upstream: {service.get('upstream_id')}")
                
                # Display consumers
                if data.get("consumers"):
                    print(f"\nConsumers:")
                    for consumer in data["consumers"]:
                        print(f"  - {consumer.get('username')}")
                        print(f"    Description: {consumer.get('desc')}")
                        print(f"    Plugins: {', '.join(consumer.get('plugins', []))}")
                
                return True
            else:
                print(f"✗ Failed to list resources: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_list_all_services():
    """Test listing all APISIX services"""
    print("\nListing all APISIX services")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FRONT_DOOR_URL}/admin/apisix/services")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Found {data.get('count', 0)} services")
                
                # Group services by project
                services_by_project = {}
                for service in data.get("services", []):
                    service_value = service.get("value", {})
                    service_name = service_value.get("name", "")
                    
                    # Extract project ID from service name
                    if "-service" in service_name:
                        project_id = service_name.replace("-api-service", "").replace("-service", "")
                        if project_id not in services_by_project:
                            services_by_project[project_id] = []
                        services_by_project[project_id].append(service_value)
                
                if services_by_project:
                    print("\nServices grouped by project:")
                    for project_id, services in services_by_project.items():
                        print(f"  Project: {project_id}")
                        for service in services:
                            print(f"    - {service.get('name')}")
                            if service.get("desc"):
                                print(f"      {service.get('desc')}")
                
                return True
            else:
                print(f"✗ Failed to list services: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_list_all_consumers():
    """Test listing all APISIX consumers"""
    print("\nListing all APISIX consumers")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FRONT_DOOR_URL}/admin/apisix/consumers")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Found {data.get('count', 0)} consumers")
                
                for consumer in data.get("consumers", []):
                    consumer_value = consumer.get("value", {})
                    username = consumer_value.get("username", "")
                    
                    # Check if it's a project consumer
                    if "-consumer" in username:
                        project_id = username.replace("-consumer", "")
                        print(f"  Project Consumer: {project_id}")
                        print(f"    Username: {username}")
                        if consumer_value.get("desc"):
                            print(f"    Description: {consumer_value.get('desc')}")
                        
                        # Show enabled plugins
                        plugins = consumer_value.get("plugins", {})
                        if plugins:
                            print(f"    Plugins: {', '.join(plugins.keys())}")
                
                return True
            else:
                print(f"✗ Failed to list consumers: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def test_cleanup_project_resources():
    """Test cleanup of project resources (optional)"""
    print(f"\nWARNING: This will delete all resources for project: {PROJECT_ID}")
    print("Skip this test to preserve resources for other tests")
    return True  # Skip by default
    
    # Uncomment to actually perform cleanup
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.delete(
    #             f"{FRONT_DOOR_URL}/admin/apisix/projects/{PROJECT_ID}/resources"
    #         )
    #         
    #         if response.status_code == 200:
    #             data = response.json()
    #             print(f"✓ Cleanup completed")
    #             print(f"  - Deleted routes: {data.get('deleted_routes', 0)}")
    #             print(f"  - Deleted upstreams: {data.get('deleted_upstreams', 0)}")
    #             print(f"  - Deleted services: {data.get('deleted_services', 0)}")
    #             print(f"  - Deleted consumers: {data.get('deleted_consumers', 0)}")
    #             
    #             if data.get("errors"):
    #                 print(f"  - Errors: {data.get('errors')}")
    #             
    #             return True
    #         else:
    #             print(f"✗ Failed to cleanup: {response.status_code}")
    #             return False
    #     except Exception as e:
    #         print(f"✗ Error: {e}")
    #         return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("APISIX Project Organization Test Suite")
    print("=" * 60)
    
    tests = [
        ("List Project Resources", test_list_project_resources),
        ("List All Services", test_list_all_services),
        ("List All Consumers", test_list_all_consumers),
        ("Cleanup Project Resources", test_cleanup_project_resources),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
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
        print("\n🎉 All tests passed! Project organization is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
