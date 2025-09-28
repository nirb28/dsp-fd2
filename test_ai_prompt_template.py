#!/usr/bin/env python3
"""
Test creating a route with ai-prompt-template plugin directly in APISIX
"""

import asyncio
import httpx
import json

async def test_ai_prompt_template_directly():
    """Test if we can create ai-prompt-template route directly"""
    
    headers = {"X-API-KEY": "edd1c9f034335f136f87ad84b625c8f1"}
    
    # Simple test route with ai-prompt-template
    test_route = {
        "name": "test-ai-prompt-template-route",
        "uri": "/test-ai-prompt",
        "methods": ["POST"],
        "upstream_id": "test-apisix-routing-groq-upstream",
        "plugins": {
            "ai-prompt-template": {
                "templates": [
                    {
                        "name": "test-template",
                        "template": {
                            "model": "llama-3.1-8b-instant",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a helpful AI assistant."
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
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("🧪 Testing ai-prompt-template plugin directly...")
            
            # Try to create the route
            response = await client.put(
                "http://localhost:9180/apisix/admin/routes/test-ai-prompt-template",
                json=test_route,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("✅ SUCCESS: ai-prompt-template route created successfully!")
                print("This means the plugin works and the issue is in the Front Door")
                
                # Test the route
                print("\n🚀 Testing the route...")
                test_payload = {
                    "template_name": "test-template",
                    "prompt": "Hello, this is a test"
                }
                
                test_response = await client.post(
                    "http://localhost:9080/test-ai-prompt",
                    json=test_payload,
                    timeout=10.0
                )
                
                print(f"Test Status: {test_response.status_code}")
                if test_response.status_code == 200:
                    print("✅ Route works! ai-prompt-template is functional")
                    try:
                        data = test_response.json()
                        print(f"Response: {json.dumps(data, indent=2)}")
                    except:
                        print(f"Response: {test_response.text}")
                else:
                    print(f"❌ Route test failed: {test_response.text}")
                
            else:
                print("❌ FAILED to create ai-prompt-template route")
                print(f"Response: {response.text}")
                
                # Check if it's a plugin validation error
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = response_data.get('error_msg', response.text)
                
                if 'ai-prompt-template' in error_msg:
                    print("🔍 This appears to be an ai-prompt-template plugin issue")
                elif 'upstream' in error_msg:
                    print("🔍 This appears to be an upstream issue")
                else:
                    print("🔍 Unknown error with route creation")
                
        except Exception as e:
            print(f"❌ Error testing ai-prompt-template: {e}")

async def check_plugin_schema():
    """Check if ai-prompt-template plugin schema is available"""
    
    headers = {"X-API-KEY": "edd1c9f034335f136f87ad84b625c8f1"}
    
    async with httpx.AsyncClient() as client:
        try:
            print("\n📋 Checking ai-prompt-template plugin schema...")
            
            response = await client.get(
                "http://localhost:9180/apisix/admin/schema/plugins/ai-prompt-template",
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ ai-prompt-template plugin schema is available")
                schema = response.json()
                print(f"Schema keys: {list(schema.keys())}")
            else:
                print(f"❌ Plugin schema not available: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error checking plugin schema: {e}")

if __name__ == "__main__":
    asyncio.run(check_plugin_schema())
    asyncio.run(test_ai_prompt_template_directly())
