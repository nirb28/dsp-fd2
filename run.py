#!/usr/bin/env python3
"""
DSP-FD2 Startup Script
Simple script to run the Front Door service
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set PYTHONPATH environment variable as well
current_pythonpath = os.environ.get('PYTHONPATH', '')
if str(project_root) not in current_pythonpath:
    if current_pythonpath:
        os.environ['PYTHONPATH'] = f"{project_root}{os.pathsep}{current_pythonpath}"
    else:
        os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='DSP Front Door (FD2)')
    parser.add_argument('--host', default=os.getenv('HOST', '0.0.0.0'), help='Host to bind to')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8080')), help='Port to bind to')
    parser.add_argument('--https-port', type=int, default=int(os.getenv('HTTPS_PORT', '8444')), help='HTTPS port to bind to')
    parser.add_argument('--reload', action='store_true', default=os.getenv('RELOAD', 'true').lower() == 'true', help='Enable auto-reload')
    parser.add_argument('--ssl', action='store_true', default=os.getenv('SSL_ENABLED', 'false').lower() == 'true', help='Enable HTTPS')
    parser.add_argument('--ssl-cert', default=os.getenv('SSL_CERT_FILE', 'certs/server.crt'), help='SSL certificate file')
    parser.add_argument('--ssl-key', default=os.getenv('SSL_KEY_FILE', 'certs/server.key'), help='SSL key file')
    parser.add_argument('--workers', type=int, default=int(os.getenv('WORKERS', '1')), help='Number of workers')
    args = parser.parse_args()
    
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Determine port and SSL settings
    if args.ssl:
        port = args.https_port
        ssl_keyfile = args.ssl_key
        ssl_certfile = args.ssl_cert
        
        # Verify SSL files exist
        if not os.path.exists(ssl_certfile):
            print(f"Error: SSL certificate not found: {ssl_certfile}")
            print("Run: python generate_ssl_certs.py")
            sys.exit(1)
        if not os.path.exists(ssl_keyfile):
            print(f"Error: SSL key not found: {ssl_keyfile}")
            print("Run: python generate_ssl_certs.py")
            sys.exit(1)
        
        print(f"Starting DSP-FD2 with HTTPS on {args.host}:{port}")
        print(f"  Certificate: {ssl_certfile}")
        print(f"  Key: {ssl_keyfile}")
        print(f"  Reload: {args.reload}, Log Level: {log_level}")
        
        if args.reload or args.workers == 1:
            # Development mode - single process with reload
            uvicorn.run(
                "src.front_door:app",
                host=args.host,
                port=port,
                reload=args.reload,
                log_level=log_level,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile
            )
        else:
            # Production mode - multiple workers
            uvicorn.run(
                "src.front_door:app",
                host=args.host,
                port=port,
                workers=args.workers,
                log_level=log_level,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile
            )
    else:
        port = args.port
        print(f"Starting DSP-FD2 with HTTP on {args.host}:{port}")
        print(f"  Reload: {args.reload}, Log Level: {log_level}")
        print("⚠ Warning: Running without HTTPS. Use --ssl for production.")
        
        if args.reload or args.workers == 1:
            # Development mode - single process with reload
            uvicorn.run(
                "src.front_door:app",
                host=args.host,
                port=port,
                reload=args.reload,
                log_level=log_level
            )
        else:
            # Production mode - multiple workers
            uvicorn.run(
                "src.front_door:app",
                host=args.host,
                port=port,
                workers=args.workers,
                log_level=log_level
            )
