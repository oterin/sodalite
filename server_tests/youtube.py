"""
testing module for instagram reels
"""

import sys
import os
import asyncio
from pprint import pprint

# so we can import server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.services import youtube as yt

async def main():
    # test url
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"fetching: {url}")

    try:
        # get the metadata
        metadata = await yt.fetch_dl(url)

        # print it out
        pprint(metadata.model_dump())
    except Exception as e:
        print(f"an error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
