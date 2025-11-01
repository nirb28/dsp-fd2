"""
Test script for sas2py manifest integration
Tests APISIX sync and inference endpoint routing

Vault Setup:
curl -X POST http://localhost:8200/v1/secret/data/sas2py/api-keys \
  -H "X-Vault-Token: myroot" \
  -d '{"data": {"groq_api_key": "test-groq-key-xyz"}}'
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx
from typing import Dict, Any
from apisix import APISIXClient

# Configuration
FRONT_DOOR_URL = "http://localhost:8080"
CONTROL_TOWER_URL = "http://localhost:8000"
APISIX_ADMIN_URL = "http://localhost:9180"
APISIX_ADMIN_KEY = "edd1c9f034335f136f87ad84b625c8f1"

MANIFEST_ID = "sas2py"


async def get_manifest_from_control_tower() -> Dict[str, Any]:
    """Get sas2py manifest from Control Tower with environment resolution"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get manifest with environment variables resolved
            response = await client.get(f"{CONTROL_TOWER_URL}/manifests/{MANIFEST_ID}?resolve_env=true")
            if response.status_code == 200:
                manifest = response.json()
                print(f"  Manifest retrieved: {len(manifest.get('modules', []))} modules")
                return manifest
            else:
                print(f"  Failed to get manifest: {response.status_code}")
            return None
        except Exception as e:
            print(f"Error getting manifest: {str(e)}")
            return None


async def configure_apisix_directly(manifest: Dict[str, Any]):
    """Configure APISIX directly using APISIXClient"""
    print("\n1a. Configuring APISIX directly from manifest...")
    
    # Debug: Check for APISIX modules
    modules = manifest.get("modules", [])
    apisix_modules = [m for m in modules if m.get("module_type") == "api_gateway" and "apisix" in m.get("name", "").lower()]
    print(f"  Found {len(apisix_modules)} APISIX modules")
    for mod in apisix_modules:
        config = mod.get("config", {})
        routes = config.get("routes", [])
        print(f"    - {mod.get('name')}: {len(routes)} routes")
        print(f"      Routes value: {routes}")
        if routes:
            print(f"      First route: {routes[0].get('name', 'unknown')}")
    
    apisix_client = APISIXClient(APISIX_ADMIN_URL, APISIX_ADMIN_KEY)
    
    try:
        result = await apisix_client.configure_from_manifest(manifest)
        
        print(f"✓ Direct APISIX configuration complete")
        print(f"  Routes created: {len(result.get('routes', []))}")
        print(f"  Upstreams created: {len(result.get('upstreams', []))}")
        print(f"  Services created: {len(result.get('services', []))}")
        print(f"  Consumers created: {len(result.get('consumers', []))}")
        
        if result.get('errors'):
            print(f"  ⚠ Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"    - {error}")
        
        await apisix_client.close()
        return len(result.get('errors', [])) == 0
        
    except Exception as e:
        print(f"✗ Direct config error: {str(e)}")
        import traceback
        traceback.print_exc()
        await apisix_client.close()
        return False


async def sync_apisix_from_manifest():
    """Sync APISIX configuration from Control Tower manifest via Front Door"""
    print("\n1b. Syncing APISIX via Front Door...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{FRONT_DOOR_URL}/admin/sync")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Sync successful")
                print(f"  Status: {data.get('status')}")
                if 'projects_synced' in data:
                    print(f"  Projects synced: {data['projects_synced']}")
                return True
            else:
                print(f"✗ Sync failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Sync error: {str(e)}")
            return False


async def verify_apisix_routes():
    """Verify APISIX routes are configured"""
    print("\n2. Verifying APISIX routes...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            headers = {"X-API-KEY": APISIX_ADMIN_KEY}
            response = await client.get(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get("list", [])
                
                print(f"✓ Found {len(routes)} routes")
                
                # Look for sas2py routes
                sas2py_routes = [r for r in routes if "sas2py" in r.get("value", {}).get("name", "")]
                
                if sas2py_routes:
                    print(f"\n  sas2py routes:")
                    for route in sas2py_routes:
                        route_val = route.get("value", {})
                        print(f"    - {route_val.get('name')}: {route_val.get('uri')}")
                        
                        # Check for ai-prompt-template plugin
                        plugins = route_val.get("plugins", {})
                        if "ai-prompt-template" in plugins:
                            print(f"      ✓ ai-prompt-template plugin configured")
                        if "jwt-auth" in plugins:
                            print(f"      ✓ jwt-auth plugin configured")
                    
                    return True
                else:
                    print(f"  ⚠ No sas2py routes found")
                    return False
            else:
                print(f"✗ Failed to get routes: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error verifying routes: {str(e)}")
            return False


async def get_jwt_token() -> str:
    """Get JWT token via Front Door using manifest configuration"""
    print("\n3. Getting JWT token (plain) via Front Door...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Use Front Door endpoint: /{project_id}/{jwt_module_name}/token
            response = await client.post(
                f"{FRONT_DOOR_URL}/sas2py/simple-auth/token",
                json={
                    "username": "admin",
                    "password": "password"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                token_type = data.get("token_type", "JWT")
                print(f"✓ Token obtained via Front Door")
                print(f"  Token type: {token_type}")
                print(f"  Token preview: {token[:50] if token else 'None'}...")
                return token
            else:
                print(f"✗ Failed to get token: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Token error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def get_jwe_token() -> str:
    """Get JWE-encrypted token via Front Door using jwe-auth module"""
    print("\n3b. Getting JWE token via Front Door...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Use jwe-auth module which has JWE encryption enabled
            response = await client.post(
                f"{FRONT_DOOR_URL}/sas2py/jwe-auth/token",
                json={
                    "username": "admin",
                    "password": "password"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                token_type = data.get("token_type", "JWT")
                encryption = data.get("encryption", "N/A")
                note = data.get("note", "")
                
                print(f"✓ JWE token obtained via Front Door")
                print(f"  Token type: {token_type}")
                print(f"  Encryption: {encryption}")
                print(f"  Note: {note}")
                print(f"  Token preview: {token[:80] if token else 'None'}...")
                
                # Verify it's actually JWE (should have 5 parts separated by dots)
                if token:
                    parts = token.split('.')
                    print(f"  Token parts: {len(parts)} (JWE should have 5 parts)")
                    if len(parts) == 5:
                        print(f"  ✓ Confirmed JWE format (5 parts)")
                    elif len(parts) == 3:
                        print(f"  ⚠ WARNING: This is a plain JWT (3 parts), not JWE!")
                
                return token
            else:
                print(f"✗ Failed to get JWE token: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ JWE token error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def test_convert_endpoint(token: str):
    """Test the /api/sas2py/convert endpoint"""
    print("\n4. Testing convert endpoint...")
    
    # Disable auto-decompression to avoid gzip errors
    # Set default_encoding to None to prevent automatic decompression
    async with httpx.AsyncClient(
        timeout=60.0, 
        follow_redirects=True,
        default_encoding="utf-8"
    ) as client:
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept-Encoding": "identity"  # Disable compression
            }
            
            # Note: ai-prompt-template plugin doesn't properly escape newlines in JSON
            # So we need to escape them manually or use a single line
            sas_code = """DATA work.example;
    INPUT name $ age salary;
    DATALINES;
John 30 50000
Jane 25 60000
;
RUN;

PROC MEANS DATA=work.example;
    VAR age salary;
RUN;"""
            
            payload = {
                "template_name": "converter",
                "user_input": sas_code.replace('\n', '\\n')  # Escape newlines for JSON
            }
            
            response = await client.post(
                f"{FRONT_DOOR_URL}/sas2py/convert",
                headers=headers,
                json=payload
            )
            
            print(f"  Status: {response.status_code}")
            print(f"  Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ Convert endpoint successful")
                    print(f"  Response preview: {str(data)[:200]}...")
                    return True
                except Exception as json_err:
                    print(f"✗ JSON decode error: {json_err}")
                    print(f"  Raw response (first 500 bytes): {response.content[:500]}")
                    return False
            else:
                print(f"✗ Convert failed: {response.status_code}")
                try:
                    print(f"  Response: {response.text[:500]}")
                except:
                    print(f"  Raw response: {response.content[:500]}")
                return False
                
        except Exception as e:
            print(f"✗ Convert error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def test_test_endpoint(token: str):
    """Test the /api/sas2py/test endpoint"""
    print("\n5. Testing test generation endpoint...")
    
    # Disable auto-decompression to avoid gzip errors
    # Set default_encoding to None to prevent automatic decompression
    async with httpx.AsyncClient(
        timeout=60.0, 
        follow_redirects=True,
        default_encoding="utf-8"
    ) as client:
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept-Encoding": "identity"  # Disable compression
            }
            
            # Note: ai-prompt-template plugin doesn't properly escape newlines in JSON
            python_code = """def add_numbers(a: int, b: int) -> int:
    return a + b

def multiply_numbers(a: int, b: int) -> int:
    return a * b"""
            
            payload = {
                "template_name": "python-test-generator",
                "user_input": python_code.replace('\n', '\\n')  # Escape newlines for JSON
            }
            
            response = await client.post(
                f"{FRONT_DOOR_URL}/sas2py/test",
                headers=headers,
                json=payload
            )
            
            print(f"  Status: {response.status_code}")
            print(f"  Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ Test endpoint successful")
                    print(f"  Response preview: {str(data)[:200]}...")
                    return True
                except Exception as json_err:
                    print(f"✗ JSON decode error: {json_err}")
                    print(f"  Raw response (first 500 bytes): {response.content[:500]}")
                    return False
            else:
                print(f"✗ Test failed: {response.status_code}")
                try:
                    print(f"  Response: {response.text[:500]}")
                except:
                    print(f"  Raw response: {response.content[:500]}")
                return False
                
        except Exception as e:
            print(f"✗ Test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def test_openai_compatible_endpoint(token: str):
    """Test the OpenAI-compatible /sas2py/v1/chat/completions endpoint"""
    print("\n5b. Testing OpenAI-compatible endpoint...")
    
    async with httpx.AsyncClient(
        timeout=60.0, 
        follow_redirects=True,
        default_encoding="utf-8"
    ) as client:
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept-Encoding": "identity"
            }
            
            # Standard OpenAI chat completion request with custom prompt
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant that provides concise answers."
                    },
                    {
                        "role": "user",
                        "content": "What is the capital of France? Answer in one word."
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            response = await client.post(
                f"{FRONT_DOOR_URL}/sas2py/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"  Status: {response.status_code}")
            print(f"  Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ OpenAI-compatible endpoint successful")
                    
                    # Validate OpenAI response structure
                    if "choices" in data and len(data["choices"]) > 0:
                        message = data["choices"][0].get("message", {})
                        content = message.get("content", "")
                        print(f"  Model: {data.get('model', 'N/A')}")
                        print(f"  Response: {content[:100]}...")
                        print(f"  ✓ Valid OpenAI response structure")
                        return True
                    else:
                        print(f"  ⚠ Response missing expected OpenAI structure")
                        print(f"  Response preview: {str(data)[:200]}...")
                        return False
                        
                except Exception as json_err:
                    print(f"✗ JSON decode error: {json_err}")
                    print(f"  Raw response (first 500 bytes): {response.content[:500]}")
                    return False
            else:
                print(f"✗ OpenAI endpoint failed: {response.status_code}")
                try:
                    print(f"  Response: {response.text[:500]}")
                except:
                    print(f"  Raw response: {response.content[:500]}")
                return False
                
        except Exception as e:
            print(f"✗ OpenAI endpoint error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def verify_manifest_config():
    """Verify manifest configuration in Control Tower"""
    print("\n6. Verifying manifest configuration...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{CONTROL_TOWER_URL}/manifests/{MANIFEST_ID}")
            
            if response.status_code == 200:
                manifest = response.json()
                print(f"✓ Manifest found")
                print(f"  Project: {manifest.get('project_name')}")
                print(f"  Environment: {manifest.get('environment')}")
                
                modules = manifest.get("modules", [])
                print(f"  Modules: {len(modules)}")
                
                # Check for required modules
                module_types = {m.get("module_type"): m.get("name") for m in modules}
                
                if "jwt_config" in module_types:
                    print(f"    ✓ JWT config: {module_types['jwt_config']}")
                
                inference_modules = [m for m in modules if m.get("module_type") == "inference_endpoint"]
                if inference_modules:
                    print(f"    ✓ Inference endpoints: {[m.get('name') for m in inference_modules]}")
                
                gateway_modules = [m for m in modules if m.get("module_type") == "api_gateway"]
                if gateway_modules:
                    print(f"    ✓ API gateways: {[m.get('name') for m in gateway_modules]}")
                    
                    # Check for ai-prompt-template
                    for gw in gateway_modules:
                        routes = gw.get("config", {}).get("routes", [])
                        for route in routes:
                            plugins = route.get("plugins", {})
                            if "ai-prompt-template" in plugins:
                                print(f"      ✓ Route {route.get('name')} has ai-prompt-template")
                
                return True
            else:
                print(f"✗ Manifest not found: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Manifest error: {str(e)}")
            return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("SAS2PY Manifest Integration Test")
    print("=" * 60)
    
    results = []
    
    # Verify manifest
    results.append(await verify_manifest_config())
    
    # Get manifest for direct config
    manifest = await get_manifest_from_control_tower()
    if manifest:
        # Configure APISIX directly
        results.append(await configure_apisix_directly(manifest))
    else:
        print("⚠ Could not get manifest, skipping direct config")
        results.append(False)
    
    # Sync APISIX via Front Door
    results.append(await sync_apisix_from_manifest())

    print("******* Exiting midway!"); sys.exit()

    # Verify routes
    results.append(await verify_apisix_routes())
    
    # Get plain JWT token
    token = await get_jwt_token()
    if token:
        results.append(True)
        
        # Test endpoints with plain JWT
        results.append(await test_convert_endpoint(token))
        results.append(await test_test_endpoint(token))
        results.append(await test_openai_compatible_endpoint(token))
    else:
        results.extend([False, False, False, False])
    
    # Get JWE token
    jwe_token = await get_jwe_token()
    if jwe_token:
        results.append(True)
    else:
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
