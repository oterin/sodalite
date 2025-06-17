"""
testing module for tiktok
"""

import sys
import os
import asyncio
from pprint import pprint

# so we can import server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.services import tiktok as tt

async def main():
    # test url
    url = "https://www.tiktok.com/@tomercarmeli666/video/7515242694759763222"
    print(f"fetching: {url}")

    try:
        # get the metadata
        metadata = await tt.fetch_dl(url)

        # print it out
        pprint(metadata.model_dump())
    except Exception as e:
        print(f"an error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
