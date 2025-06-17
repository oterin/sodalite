"""
testing module for instagram reels
"""

import sys
import os
import asyncio

import server.services.instagram_reels as igreels

async def run_test():

    # test url
    url = "https://www.instagram.com/reels/DK8oTsHMJjY/"
    print(f"Attempting to extract data from: {url}")

    url = await igreels.fetchdl(url)

    print(f"Extracted URL: {url}")

if __name__ == "__main__":
    asyncio.run(run_test())
