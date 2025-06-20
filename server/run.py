"""
development server runner for sodalite
"""

import uvicorn
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv("server.env")

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=1335,
        reload=True,
        log_level="info",
        ssl_keyfile=os.getenv("SSL_KEYFILE"),
        ssl_certfile=os.getenv("SSL_CERTFILE"),
        workers=1
    )
