"""
Mock service routes integrated into the main FD app.
Provides httpbin and OpenAI mock endpoints under /mock/* paths.
"""
import json
import time
import uuid
import base64
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Response, Header
from fastapi.responses import StreamingResponse, JSONResponse


router = APIRouter(prefix="/mock", tags=["mock-services"])


@router.get("/httpbin/get")
async def mock_httpbin_get(request: Request):
    """Simulates httpbin.org/get - returns GET request data"""
    return JSONResponse({
        'args': dict(request.query_params),
        'headers': dict(request.headers),
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.post("/httpbin/post")
async def mock_httpbin_post(request: Request):
    """Simulates httpbin.org/post - returns POST request data"""
    data = None
    json_data = None
    
    try:
        json_data = await request.json()
    except:
        pass
    
    try:
        body = await request.body()
        if body:
            data = body.decode('utf-8')
    except:
        pass
    
    return JSONResponse({
        'args': dict(request.query_params),
        'data': data,
        'files': {},
        'form': {},
        'headers': dict(request.headers),
        'json': json_data,
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.put("/httpbin/put")
async def mock_httpbin_put(request: Request):
    """Simulates httpbin.org/put - returns PUT request data"""
    data = None
    json_data = None
    
    try:
        json_data = await request.json()
    except:
        pass
    
    try:
        body = await request.body()
        if body:
            data = body.decode('utf-8')
    except:
        pass
    
    return JSONResponse({
        'args': dict(request.query_params),
        'data': data,
        'files': {},
        'form': {},
        'headers': dict(request.headers),
        'json': json_data,
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.delete("/httpbin/delete")
async def mock_httpbin_delete(request: Request):
    """Simulates httpbin.org/delete - returns DELETE request data"""
    return JSONResponse({
        'args': dict(request.query_params),
        'headers': dict(request.headers),
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.get("/httpbin/headers")
async def mock_httpbin_headers(request: Request):
    """Simulates httpbin.org/headers - returns request headers"""
    return JSONResponse({
        'headers': dict(request.headers)
    })


@router.api_route("/httpbin/status/{code}", methods=["GET", "POST", "PUT", "DELETE"])
async def mock_httpbin_status(code: int):
    """Simulates httpbin.org/status/<code> - returns specified status code"""
    return Response('', status_code=code)


@router.get("/httpbin/delay/{seconds}")
async def mock_httpbin_delay(seconds: int, request: Request):
    """Simulates httpbin.org/delay/<seconds> - delays response"""
    await asyncio.sleep(min(seconds, 10))
    return JSONResponse({
        'args': dict(request.query_params),
        'headers': dict(request.headers),
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.get("/httpbin/basic-auth/{username}/{password}")
async def mock_httpbin_basic_auth(username: str, password: str, authorization: str = Header(None)):
    """Simulates httpbin.org/basic-auth - requires basic authentication"""
    if not authorization or not authorization.startswith('Basic '):
        return Response(
            'Unauthorized',
            status_code=401,
            headers={'WWW-Authenticate': 'Basic realm="Login Required"'}
        )
    
    try:
        encoded = authorization.replace('Basic ', '')
        decoded = base64.b64decode(encoded).decode('utf-8')
        auth_username, auth_password = decoded.split(':', 1)
        
        if auth_username != username or auth_password != password:
            return Response('Unauthorized', status_code=401)
    except:
        return Response('Unauthorized', status_code=401)
    
    return JSONResponse({
        'authenticated': True,
        'user': username
    })


@router.get("/httpbin/bearer")
async def mock_httpbin_bearer(authorization: str = Header(None)):
    """Simulates httpbin.org/bearer - requires bearer token authentication"""
    if not authorization or not authorization.startswith('Bearer '):
        return Response('Unauthorized', status_code=401)
    
    token = authorization.replace('Bearer ', '')
    
    return JSONResponse({
        'authenticated': True,
        'token': token
    })


@router.get("/httpbin/json")
async def mock_httpbin_json():
    """Simulates httpbin.org/json - returns sample JSON"""
    return JSONResponse({
        'slideshow': {
            'author': 'Yours Truly',
            'date': 'date of publication',
            'slides': [
                {
                    'title': 'Wake up to WonderWidgets!',
                    'type': 'all'
                },
                {
                    'items': [
                        'Why <em>WonderWidgets</em> are great',
                        'Who <em>buys</em> WonderWidgets'
                    ],
                    'title': 'Overview',
                    'type': 'all'
                }
            ],
            'title': 'Sample Slide Show'
        }
    })


@router.get("/httpbin/uuid")
async def mock_httpbin_uuid():
    """Simulates httpbin.org/uuid - returns a UUID"""
    return JSONResponse({
        'uuid': str(uuid.uuid4())
    })


@router.get("/httpbin/base64/{value}")
async def mock_httpbin_base64_decode(value: str):
    """Simulates httpbin.org/base64 - decodes base64 string"""
    try:
        decoded = base64.b64decode(value).decode('utf-8')
        return Response(decoded, media_type='text/plain')
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)


@router.api_route("/httpbin/response-headers", methods=["GET", "POST"])
async def mock_httpbin_response_headers(request: Request):
    """Simulates httpbin.org/response-headers - returns custom headers"""
    response_data = {
        'Content-Type': request.query_params.get('Content-Type', 'application/json')
    }
    
    for key, value in request.query_params.items():
        response_data[key] = value
    
    resp = JSONResponse(response_data)
    
    for key, value in request.query_params.items():
        if key != 'Content-Type':
            resp.headers[key] = value
    
    return resp


@router.api_route("/httpbin/anything", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/httpbin/anything/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def mock_httpbin_anything(request: Request, path: str = None):
    """Simulates httpbin.org/anything - returns anything sent"""
    data = None
    json_data = None
    
    try:
        json_data = await request.json()
    except:
        pass
    
    try:
        body = await request.body()
        if body:
            data = body.decode('utf-8')
    except:
        pass
    
    return JSONResponse({
        'args': dict(request.query_params),
        'data': data,
        'files': {},
        'form': {},
        'headers': dict(request.headers),
        'json': json_data,
        'method': request.method,
        'origin': request.client.host if request.client else 'unknown',
        'url': str(request.url)
    })


@router.get("/httpbin/health")
async def mock_httpbin_health():
    """Health check endpoint for httpbin mock"""
    return JSONResponse({
        'status': 'healthy',
        'service': 'httpbin-mock',
        'timestamp': datetime.utcnow().isoformat()
    })


def generate_chat_completion_response(messages, model, stream=False, **kwargs):
    """Generate a mock chat completion response"""
    last_message = messages[-1] if messages else {"role": "user", "content": ""}
    user_content = last_message.get("content", "")
    
    mock_response = f"This is a mock response to: {user_content}"
    
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    if stream:
        return generate_streaming_response(completion_id, model, mock_response, created)
    else:
        return generate_non_streaming_response(completion_id, model, mock_response, created)


def generate_non_streaming_response(completion_id, model, content, created):
    """Generate a non-streaming chat completion response"""
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": len(content.split()),
            "total_tokens": 10 + len(content.split())
        }
    }


def generate_streaming_response(completion_id, model, content, created):
    """Generate a streaming chat completion response"""
    async def generate():
        words = content.split()
        
        for i, word in enumerate(words):
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": word + " " if i < len(words) - 1 else word
                        },
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.05)
        
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@router.post("/openai/v1/chat/completions")
async def mock_openai_chat_completions(request: Request):
    """Simulates OpenAI Chat Completions API endpoint"""
    try:
        data = await request.json()
        
        if not data:
            return JSONResponse(
                {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}},
                status_code=400
            )
        
        messages = data.get('messages', [])
        model = data.get('model', 'gpt-3.5-turbo')
        stream = data.get('stream', False)
        
        if not messages:
            return JSONResponse({
                "error": {
                    "message": "messages is required",
                    "type": "invalid_request_error"
                }
            }, status_code=400)
        
        response = generate_chat_completion_response(
            messages=messages,
            model=model,
            stream=stream,
            **data
        )
        
        if stream:
            return response
        else:
            return JSONResponse(response)
    
    except Exception as e:
        return JSONResponse({
            "error": {
                "message": str(e),
                "type": "internal_server_error"
            }
        }, status_code=500)


@router.get("/openai/v1/models")
async def mock_openai_list_models():
    """Simulates OpenAI Models API endpoint"""
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            },
            {
                "id": "gpt-3.5-turbo-16k",
                "object": "model",
                "created": 1683758102,
                "owned_by": "openai"
            }
        ]
    })


@router.get("/openai/v1/models/{model_id}")
async def mock_openai_get_model(model_id: str):
    """Simulates OpenAI Get Model API endpoint"""
    return JSONResponse({
        "id": model_id,
        "object": "model",
        "created": 1687882411,
        "owned_by": "openai"
    })


@router.post("/openai/v1/completions")
async def mock_openai_completions(request: Request):
    """Simulates OpenAI Completions API endpoint (legacy)"""
    try:
        data = await request.json()
        
        if not data:
            return JSONResponse(
                {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}},
                status_code=400
            )
        
        prompt = data.get('prompt', '')
        model = data.get('model', 'text-davinci-003')
        
        completion_id = f"cmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        
        mock_text = f"This is a mock completion for prompt: {prompt}"
        
        return JSONResponse({
            "id": completion_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "text": mock_text,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(mock_text.split()),
                "total_tokens": len(prompt.split()) + len(mock_text.split())
            }
        })
    
    except Exception as e:
        return JSONResponse({
            "error": {
                "message": str(e),
                "type": "internal_server_error"
            }
        }, status_code=500)


@router.post("/openai/v1/embeddings")
async def mock_openai_embeddings(request: Request):
    """Simulates OpenAI Embeddings API endpoint"""
    try:
        data = await request.json()
        
        if not data:
            return JSONResponse(
                {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}},
                status_code=400
            )
        
        input_text = data.get('input', '')
        model = data.get('model', 'text-embedding-ada-002')
        
        if isinstance(input_text, str):
            input_list = [input_text]
        else:
            input_list = input_text
        
        embeddings_data = []
        for i, text in enumerate(input_list):
            mock_embedding = [0.1] * 1536
            embeddings_data.append({
                "object": "embedding",
                "embedding": mock_embedding,
                "index": i
            })
        
        return JSONResponse({
            "object": "list",
            "data": embeddings_data,
            "model": model,
            "usage": {
                "prompt_tokens": sum(len(t.split()) for t in input_list),
                "total_tokens": sum(len(t.split()) for t in input_list)
            }
        })
    
    except Exception as e:
        return JSONResponse({
            "error": {
                "message": str(e),
                "type": "internal_server_error"
            }
        }, status_code=500)


@router.get("/openai/health")
async def mock_openai_health():
    """Health check endpoint for OpenAI mock"""
    return JSONResponse({
        'status': 'healthy',
        'service': 'openai-mock',
        'timestamp': datetime.utcnow().isoformat()
    })


import asyncio
