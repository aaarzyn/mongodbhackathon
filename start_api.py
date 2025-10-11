"""Start the FastAPI server.

Usage:
    python start_api.py
    
Or with uvicorn directly:
    uvicorn backend.api.app:app --reload
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

