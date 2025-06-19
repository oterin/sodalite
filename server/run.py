"""
development server runner for sodalite
"""

import uvicorn
from server.main import app

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # auto-reload on code changes
        log_level="info"
    )
