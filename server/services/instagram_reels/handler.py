"""
sodalite service for instagram reels
"""

from server.helper.errors import InstagramReelsError
from server.models.metadata import SodaliteMetadata, VideoQuality, AudioQuality, Author
from pydantic import HttpUrl
from typing import List
import aiohttp
import re
import json

async def _get_raw_data(url: str) -> str:
    """
    fetches the raw html from the instagram reels url
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
                raise InstagramReelsError(f"failed to fetch data from {url}")
            return await response.text(encoding='utf-8', errors='ignore')

def _extract_json_from_raw_data(raw_data: str) -> dict:
    """
    extracts the json data from the raw html
    """
    pattern = r'\s*<script[^>]*data-content-len[^>]*data-sjs[^>]*>([^<]*)</script>'
    matches = re.findall(pattern, raw_data)
    if not matches:
        raise InstagramReelsError("could not find json data in the response")

    for match in matches:
        try:
            if "video_dash_manifest" in match:
                return json.loads(match)
        except json.JSONDecodeError:
            continue
    raise InstagramReelsError("could not find json data with video_dash_manifest")

def _parse_metadata_from_json(json_data: dict, source_url: str) -> SodaliteMetadata:
    """
    parses the json data and returns a SodaliteMetadata object
    """
    try:
        media_data = json_data["require"][0][3][0]["__bbox"]["require"][0][3][1]["__bbox"]["result"]["data"]["xdt_api__v1__clips__clips_on_logged_out_connection_v2"]["edges"][0]["node"]["media"]
    except (KeyError, IndexError, TypeError):
        raise InstagramReelsError("could not find media data in json structure")

    videos: List[VideoQuality] = []
    for version in media_data.get("video_versions", []):
        if version.get("url"):
            videos.append(VideoQuality(
                url=version["url"],
                quality_label=f'{version.get("height", "unknown")}p',
                width=version.get("width"),
                height=version.get("height"),
                mime_type=version.get("mime_type", "video/mp4")
            ))

    # instagram doesn't provide separate audio streams in this json, so we leave it empty
    audios: List[AudioQuality] = []

    author_data = media_data.get("owner", {})

    profile_url = None
    if author_data.get("username"):
        profile_url = HttpUrl(f'https://instagram.com/{author_data.get("username")}')

    author = Author(
        username=author_data.get("username", "unknown"),
        display_name=author_data.get("full_name"),
        profile_url=profile_url,
        avatar_url=author_data.get("profile_pic_url")
    )

    title = media_data.get("title") or f"instagram reel by {author.username}"
    description = None
    if media_data.get("edge_media_to_caption", {}).get("edges"):
        description = media_data["edge_media_to_caption"]["edges"][0]["node"]["text"]


    return SodaliteMetadata(
        service="instagram_reels",
        source_url=HttpUrl(source_url),
        title=title,
        description=description,
        author=author,
        thumbnail_url=media_data.get("display_url"),
        videos=videos,
        audios=audios
    )

async def fetch_dl(url: str) -> SodaliteMetadata:
    """
    takes in a raw instagram reels url, and returns the metadata
    """
    raw_data = await _get_raw_data(url)
    json_data = _extract_json_from_raw_data(raw_data)
    metadata = _parse_metadata_from_json(json_data, url)
    return metadata
