"""
sodalite service for instagram reels
"""

# error importing
from server.helper.errors import *

# standard library imports
import aiohttp
import re
import json

# helper functions
async def extract_json_from_raw_url(url: str) -> dict:
    """
    takes in a raw instagram reels url, and returns a dictionary with the reel data
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if not response.ok:
                raise InstagramReelsError(f"Failed to fetch data from {url}")

            raw_data = await response.text(encoding='utf-8', errors='ignore')

            # let's find the script tag with the JSON data using regex my most trusted friend
            # e.g. <script type="application/json" data-content-len="xxxxxx" data-sjs>
            pattern = r'\s*<script[^>]*data-content-len[^>]*data-sjs[^>]*>([^<]*)</script>'
            matches = re.findall(pattern, raw_data)

            if not matches:
                raise InstagramReelsError("Could not find JSON data in the response :(")

            # look for the one with video_dash_manifest
            json_data = None
            for match in matches:
                try:
                    if "video_dash_manifest" in match:
                        json_data = json.loads(match)
                        break
                except json.JSONDecodeError:
                    continue

            if not json_data:
                raise InstagramReelsError("Could not find JSON data with video_dash_manifest :(")

            # found you 8)
            return json_data
    return {}

async def extract_cdn_link_from_json(json_data: dict) -> str:
    """
    extracts the cdn link from the json data
    """
    # navigate through the nested structure to find media items
    try:
        # i know this is really ugly, but this is the only way to get the data
        edges = json_data["require"][0][3][0]["__bbox"]["require"][0][3][1]["__bbox"]["result"]["data"]["xdt_api__v1__clips__clips_on_logged_out_connection_v2"]["edges"]
    except (KeyError, IndexError, TypeError):
        raise InstagramReelsError("Could not find media data in JSON structure")

    # find the media with the highest quality video version (hack for now - no quality selection)
    best_url = None
    highest_width = 0

    for edge in edges:
        try:
            media = edge["node"]["media"]
            video_versions = media.get("video_versions", [])

            # let's find the best quality
            for version in video_versions:
                url = version.get("url", "")
                # type 101 seems to be the standard video type (correct me if i'm wrong github)
                if url and version.get("type") == 101:
                    best_url = url
                    break

            # ka-ching.
            if best_url:
                break

        except (KeyError, TypeError):
            continue

    if not best_url:
        raise InstagramReelsError("No video URL found in the JSON data")

    return best_url

async def fetchdl(url: str) -> str:
    """
    takes in a raw instagram reels url, and returns the cdn link for the video
    """
    # extract the JSON data from the URL
    json_data = await extract_json_from_raw_url(url)

    # extract the CDN link from the JSON data
    cdn_link = await extract_cdn_link_from_json(json_data)

    return cdn_link
