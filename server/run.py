"""
development server runner for sodalite
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=1337,
        reload=True,
        log_level="info"
    )
