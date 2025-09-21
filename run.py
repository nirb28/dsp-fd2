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
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    workers = int(os.getenv("WORKERS", 1))
    
    print(f"Starting DSP-FD2 on {host}:{port}")
    print(f"Reload: {reload}, Log Level: {log_level}")
    
    if reload or workers == 1:
        # Development mode - single process with reload
        uvicorn.run(
            "src.front_door:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level
        )
    else:
        # Production mode - multiple workers
        uvicorn.run(
            "src.front_door:app",
            host=host,
            port=port,
            workers=workers,
            log_level=log_level
        )
