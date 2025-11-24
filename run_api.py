"""Simple API launcher that definitely works."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("\n🚀 Starting Research Agent API...\n")
    
    from API.fastapi_app import app
    import uvicorn
    
    # Use 127.0.0.1 instead of 0.0.0.0 for Windows
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
    
    server = uvicorn.Server(config)
    
    print(f"✓ Server running at: http://127.0.0.1:8000")
    print(f"✓ API docs at: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")