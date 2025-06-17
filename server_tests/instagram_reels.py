"""
testing module for instagram reels
"""

import sys
import os
import asyncio
from pprint import pprint

# so we can import server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.services import instagram_reels as igreels

async def main():
    # test url
    url = "https://www.instagram.com/reels/DG015nWMouI/"
    print(f"fetching: {url}")

    try:
        # get the metadata
        metadata = await igreels.fetch_dl(url)

        # print it out
        print("\n--- metadata ---")
        pprint(metadata.model_dump())
        print("------------------")

    except Exception as e:
        print(f"an error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
