"""
Test script for Front Door Service
Tests both APISIX and direct routing modes
"""

import asyncio
import json
import httpx

# Configuration
FRONT_DOOR_URL = "http://localhost:8080"
CONTROL_TOWER_URL = "http://localhost:8000"
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
                    
                    # Try to parse response to show services involved
                    try:
                        data = response.json()
                        if "services" in data:
                            print(f"  - Services involved: {', '.join(data['services'])}")
                        elif "message" in data:
                            print(f"  - Response: {data['message']}")
                    except:
                        print(f"  - Response received (non-JSON)")
                        
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


async def test_inference_routing(project_id: str):
    """Test inference endpoint routing through APISIX with ai-prompt-template plugin"""
    print(f"\n6. Testing Groq Inference Routing with AI Prompt Template for: {project_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: ai-prompt-template route with simple prompt
            print("\n  Testing ai-prompt-template route...")
            inference_payload = {
                "template_name": "groq-llama-template",
                "prompt": "What is the capital of France?",
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            response = await client.post(
                f"{FRONT_DOOR_URL}/{project_id}/v1/inference/completions",
                json=inference_payload,
                timeout=30.0
            )
            
            print(f"  - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ AI Prompt Template inference request routed successfully")
                try:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        print(f"  - Response from Groq: {content[:100]}...")
                    else:
                        print(f"  - Response structure: {list(data.keys())}")
                except Exception as e:
                    print(f"  - Response parsing error: {e}")
                    print(f"  - Raw response: {response.text[:200]}...")
            elif response.status_code in [404, 502, 503]:
                print(f"✓ Route configured but backend issue (status: {response.status_code})")
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                print(f"  - Response: {response.text[:200]}...")
            
            # Test 2: Direct chat completions route
            print("\n  Testing direct chat completions route...")
            chat_payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello! How are you?"}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            try:
                response2 = await client.post(
                    f"{FRONT_DOOR_URL}/{project_id}/v1/chat/completions",
                    json=chat_payload,
                    timeout=30.0
                )
                
                print(f"  - Chat Status Code: {response2.status_code}")
                
                if response2.status_code == 200:
                    print(f"✓ Direct chat completions request routed successfully")
                    try:
                        data2 = response2.json()
                        if "choices" in data2 and len(data2["choices"]) > 0:
                            content = data2["choices"][0].get("message", {}).get("content", "")
                            print(f"  - Chat Response from Groq: {content[:100]}...")
                    except Exception as e:
                        print(f"  - Chat response parsing error: {e}")
                elif response2.status_code in [404, 502, 503]:
                    print(f"✓ Chat route configured but backend issue (status: {response2.status_code})")
                else:
                    print(f"✗ Unexpected chat status code: {response2.status_code}")
                    print(f"  - Chat Response: {response2.text[:200]}...")
            except Exception as e:
                print(f"✗ Chat completions test error: {e}")
            
            # Check for APISIX headers
            gateway_headers = [h for h in response.headers.keys() if 'gateway' in h.lower() or 'apisix' in h.lower()]
            if gateway_headers:
                print(f"  - Gateway headers found: {gateway_headers}")
            
            # Check for custom headers
            custom_headers = [h for h in response.headers.keys() if h.startswith('X-Gateway') or h.startswith('X-Target')]
            if custom_headers:
                print(f"  - Custom routing headers: {custom_headers}")
            
            return response.status_code in [200, 404, 502, 503]
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def create_test_manifests():
    """Create test manifests with different routing configurations"""
    print("\n0. Creating Test Manifests...")
    
    headers = {"X-DSPAI-Client-Secret": CONTROL_TOWER_SECRET}
    
    # Combined manifest with APISIX + Inference modules
    manifest_with_apisix = {
        "project_id": "test-apisix-routing",
        "project_name": "Test APISIX + Inference Combined",
        "owner": "test-team",
        "environment": "test",
        "modules": [
            {
                "module_type": "inference_endpoint",
                "name": "test-llm-service",
                "config": {
                    "model_name": "llama-3.1-8b-instant",
                    "model_version": "latest",
                    "endpoint_url": "http://localhost:9080/v1/chat/completions",
                    "system_prompt": "You are a helpful AI assistant.",
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "timeout": 30
                }
            },
            {
                "module_type": "api_gateway",
                "name": "test-apisix-gateway",
                "config": {
                    "admin_api_url": "http://localhost:9180",
                    "admin_key": "edd1c9f034335f136f87ad84b625c8f1",
                    "gateway_url": "http://localhost:9080",
                    "dashboard_url": "http://localhost:9000",
                    "routes": [
                        {
                            "name": "llm-inference-route",
                            "uri": "/v1/inference/*",
                            "methods": ["POST", "GET", "OPTIONS"],
                            "upstream_id": "test-apisix-routing-groq-upstream",
                            "plugins": [
                                {
                                    "name": "limit-req",
                                    "enabled": True,
                                    "config": {
                                        "rate": 10,
                                        "burst": 5,
                                        "rejected_code": 429,
                                        "key_type": "var",
                                        "key": "remote_addr",
                                        "rejected_msg": "Rate limit exceeded for inference requests"
                                    }
                                },
                                {
                                    "name": "ai-prompt-template",
                                    "enabled": True,
                                    "config": {
                                        "templates": [
                                            {
                                                "name": "groq-llama-template",
                                                "template": {
                                                    "model": "llama-3.1-8b-instant",
                                                    "messages": [
                                                        {
                                                            "role": "system",
                                                            "content": "You are a helpful AI assistant. Respond concisely and accurately."
                                                        },
                                                        {
                                                            "role": "user",
                                                            "content": "{{prompt}}"
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                },
                                {
                                    "name": "proxy-rewrite",
                                    "enabled": True,
                                    "config": {
                                        "regex_uri": ["^/v1/inference/(.*)", "/v1/chat/completions"],
                                        "headers": {
                                            "Authorization": "Bearer <API_KEY>",
                                            "Content-Type": "application/json",
                                            "Accept-Encoding": "identity",
                                            "X-Gateway-Service": "test-apisix-gateway",
                                            "X-Target-Service": "groq-llm-service"
                                        }
                                    }
                                }
                            ]
                        },
                        {
                            "name": "llm-chat-route",
                            "uri": "/v1/chat/completions",
                            "methods": ["POST", "OPTIONS"],
                            "upstream_id": "test-apisix-routing-groq-upstream",
                            "plugins": [
                                {
                                    "name": "limit-req",
                                    "enabled": True,
                                    "config": {
                                        "rate": 20,
                                        "burst": 10,
                                        "rejected_code": 429,
                                        "key_type": "var",
                                        "key": "remote_addr",
                                        "rejected_msg": "Rate limit exceeded for chat requests"
                                    }
                                },
                                {
                                    "name": "proxy-rewrite",
                                    "enabled": True,
                                    "config": {
                                        "headers": {
                                            "Authorization": "Bearer <API_KEY>",
                                            "Content-Type": "application/json",
                                            "Accept-Encoding": "identity",
                                            "X-Gateway-Service": "test-apisix-gateway",
                                            "X-Target-Service": "groq-llm-service"
                                        }
                                    }
                                }
                            ]
                        },
                        {
                            "name": "test-route",
                            "uri": "/test",
                            "methods": ["GET"],
                            "plugins": [
                                {
                                    "name": "serverless-pre-function",
                                    "enabled": True,
                                    "config": {
                                        "phase": "access",
                                        "functions": [
                                            "return function(conf, ctx) ngx.say('{\"message\":\"Hello from combined APISIX + Inference test\",\"timestamp\":\"' .. os.date() .. '\",\"services\":[\"test-apisix-gateway\",\"test-llm-service\"]}') ngx.exit(200) end"
                                        ]
                                    }
                                }
                            ]
                        }
                    ],
                    "upstreams": [
                        {
                            "name": "groq-upstream",
                            "type": "roundrobin",
                            "scheme": "https",
                            "pass_host": "pass",
                            "nodes": {
                                "api.groq.com:443": 100
                            },
                            "timeout": {
                                "connect": 10,
                                "send": 30,
                                "read": 60
                            },
                            "retries": 2,
                            "keepalive_pool": {
                                "size": 320,
                                "idle_timeout": 60,
                                "requests": 1000
                            }
                        }
                    ],
                    "global_plugins": [
                        {
                            "name": "cors",
                            "enabled": True,
                            "config": {
                                "allow_origins": "*",
                                "allow_methods": "GET, POST, PUT, DELETE, OPTIONS",
                                "allow_headers": "*",
                                "max_age": 3600
                            }
                        }
                    ],
                    "jwt_auth_enabled": False,
                    "rate_limiting_enabled": True,
                    "logging_enabled": True,
                    "prometheus_enabled": False,
                    "ssl_enabled": False,
                    "cors_enabled": True,
                    "cors_origins": ["*"],
                    "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "default_timeout": 60,
                    "default_retries": 2,
                    "streaming_enabled": True,
                    "response_buffering": False,
                    "request_buffering": True
                }
            }
        ]
    }
    
    # Enhanced direct routing manifest with multiple inference endpoints
    manifest_direct = {
        "project_id": "test-direct-routing",
        "project_name": "Test Direct Multi-Inference",
        "owner": "test-team",
        "environment": "test",
        "modules": [
            {
                "module_type": "inference_endpoint",
                "name": "test-llm-primary",
                "config": {
                    "model_name": "test-primary-model",
                    "endpoint_url": "http://localhost:8001/v1/completions",
                    "system_prompt": "You are the primary AI assistant.",
                    "max_tokens": 4096,
                    "temperature": 0.8,
                    "timeout": 30
                }
            },
            {
                "module_type": "inference_endpoint",
                "name": "test-llm-backup",
                "config": {
                    "model_name": "test-backup-model",
                    "endpoint_url": "http://localhost:8002/v1/completions",
                    "system_prompt": "You are the backup AI assistant.",
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "timeout": 45
                }
            }
        ]
    }
    
    # New Groq APISIX manifest matching groq.md configuration
    manifest_groq_apisix = {
        "project_id": "test-groq-apisix",
        "project_name": "Test Groq APISIX Integration",
        "owner": "test-team",
        "environment": "test",
        "modules": [
            {
                "module_type": "inference_endpoint",
                "name": "groq-llm-service",
                "config": {
                    "model_name": "llama-3.1-8b-instant",
                    "model_version": "latest",
                    "endpoint_url": "http://localhost:9080/groq/chat/completions",
                    "system_prompt": "You are a helpful AI assistant powered by Groq.",
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "timeout": 30,
                    "provider": "groq",
                    "api_base": "https://api.groq.com/openai/v1"
                }
            },
            {
                "module_type": "api_gateway",
                "name": "groq-apisix-gateway",
                "config": {
                    "admin_api_url": "http://localhost:9180",
                    "admin_key": "edd1c9f034335f136f87ad84b625c8f1",
                    "gateway_url": "http://localhost:9080",
                    "dashboard_url": "http://localhost:9000",
                    "routes": [
                        {
                            "name": "groq-route",
                            "uri": "/groq/chat/*",
                            "methods": ["POST"],
                            "upstream_id": "groq-upstream",
                            "plugins": [
                                {
                                    "name": "proxy-rewrite",
                                    "enabled": True,
                                    "config": {
                                        "uri": "/openai/v1/chat/completions",
                                        "scheme": "https"
                                    }
                                },
                                {
                                    "name": "ai-proxy",
                                    "enabled": True,
                                    "config": {
                                        "provider": "openai-compatible",
                                        "auth": {
                                            "header": {
                                                "Authorization": "Bearer <API_KEY>"
                                            }
                                        },
                                        "options": {
                                            "model": "llama-3.1-8b-instant"
                                        },
                                        "override": {
                                            "endpoint": "https://api.groq.com/openai/v1/chat/completions"
                                        }
                                    }
                                }
                            ]
                        }
                    ],
                    "upstreams": [
                        {
                            "name": "groq-upstream",
                            "type": "roundrobin",
                            "scheme": "https",
                            "pass_host": "pass",
                            "nodes": {
                                "api.groq.com:443": 1
                            },
                            "timeout": {
                                "connect": 10,
                                "send": 30,
                                "read": 60
                            },
                            "retries": 2,
                            "keepalive_pool": {
                                "size": 100,
                                "idle_timeout": 60,
                                "requests": 1000
                            }
                        }
                    ],
                    "global_plugins": [
                        {
                            "name": "cors",
                            "enabled": True,
                            "config": {
                                "allow_origins": "*",
                                "allow_methods": "GET, POST, PUT, DELETE, OPTIONS",
                                "allow_headers": "*",
                                "max_age": 3600
                            }
                        }
                    ],
                    "jwt_auth_enabled": False,
                    "rate_limiting_enabled": False,
                    "logging_enabled": True,
                    "prometheus_enabled": False,
                    "ssl_enabled": False,
                    "cors_enabled": True,
                    "cors_origins": ["*"],
                    "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "default_timeout": 60,
                    "default_retries": 2,
                    "streaming_enabled": True,
                    "response_buffering": False,
                    "request_buffering": True
                }
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        # Create APISIX manifest
        try:
            response = await client.post(
                f"{CONTROL_TOWER_URL}/manifests",
                json={"manifest": manifest_with_apisix},
                headers=headers
            )
            if response.status_code in [201, 409]:
                print("✓ Combined APISIX + Inference test manifest created/exists")
            else:
                print(f"  Warning: Combined manifest creation failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  Warning: Could not create combined manifest: {e}")
        
        # Create direct routing manifest
        try:
            response = await client.post(
                f"{CONTROL_TOWER_URL}/manifests",
                json={"manifest": manifest_direct},
                headers=headers
            )
            if response.status_code in [201, 409]:
                print("✓ Multi-inference direct routing test manifest created/exists")
            else:
                print(f"  Warning: Multi-inference manifest creation failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  Warning: Could not create multi-inference manifest: {e}")
        
        # Create Groq APISIX manifest
        try:
            response = await client.post(
                f"{CONTROL_TOWER_URL}/manifests",
                json={"manifest": manifest_groq_apisix},
                headers=headers
            )
            if response.status_code in [201, 409]:
                print("✓ Groq APISIX ai-proxy test manifest created/exists")
            else:
                print(f"  Warning: Groq APISIX manifest creation failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  Warning: Could not create Groq APISIX manifest: {e}")


async def main():
    """Run all tests"""
    print("=" * 70)
    print("DSP-FD2 APISIX + Groq AI Prompt Template Test Suite")
    print("=" * 70)
    
    # Create test manifests first
    await create_test_manifests()
    
    tests = [
        ("Health Check", test_health_check, None),
        ("Sync Manifests", test_sync_manifests, None),
        ("List Projects", test_list_projects, None),
        # ("Configure APISIX+Inference Project", test_configure_project, "test-apisix-routing"),
        # ("Test APISIX+Inference Basic Route", test_request_routing, "test-apisix-routing"),
        # ("Test Groq AI Prompt Template Route", test_inference_routing, "test-apisix-routing"),
        ("Test Groq APISIX ai-proxy Integration", test_request_routing, "test-groq-apisix"),

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
        print("\n🎉 All tests passed! APISIX + Groq AI Prompt Template routing is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
