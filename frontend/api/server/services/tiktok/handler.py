"""
sodalite service for tiktok
"""

import aiohttp
import json
import re
from typing import List, Optional, Dict, Tuple

# le shared modules
from server.models.metadata import SodaliteMetadata, Video, Audio
from server.helper.errors import TikTokError

async def _get_raw_data(url: str) -> Tuple[str, Dict[str, str]]:
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'DNT': '1',
        'Pragma': 'no-cache',
        'Sec-CH-UA': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    }

    cookies = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if not response.ok:
                raise TikTokError(f"Failed to fetch data from {url}, status: {response.status}")

            # Extract cookies from response
            for cookie in response.cookies.values():
                cookies[cookie.key] = cookie.value

            return await response.text(encoding='utf-8', errors='ignore'), cookies

def _extract_json_from_raw_data(raw_data: str) -> dict:
    """
    extracts the main json data blob from the raw html
    """
    # drink water, stay hydrated
    pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
    match = re.search(pattern, raw_data, re.DOTALL)

    if not match:
        raise TikTokError("Could not find __UNIVERSAL_DATA_FOR_REHYDRATION__ script tag.")

    json_str = match.group(1)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        raise TikTokError(f"Failed to parse JSON from the script tag.")

def _parse_metadata_from_json(json_data: dict, cookies: Dict[str, str]) -> SodaliteMetadata:
    """
    parses the metadata from the JSON data
    """

    try:
        # navigate to the core data structure
        item_struct = json_data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
        video_info = item_struct.get("video", {})
        music_info = item_struct.get("music", {})
        author_info = item_struct.get("author", {})
    except KeyError as e:
        raise TikTokError(f"Missing expected key in JSON data: {e}")


    videos: List[Video] = []
    audios: List[Audio] = []

    # extract audio-only stream (if available)
    if music_info.get("playUrl"):
        audios.append(Audio(
            url=music_info["playUrl"],
            quality="original", # tiktok doesn't tell us the bitrate :(
            headers={
                'Cookie': '; '.join([f"{k}={v}" for k, v in cookies.items()])
            } if cookies else None
        ))

    # add other available bitrates (likely video-only for dash streams)
    bitrate_info_list = video_info.get("bitrateInfo", [])
    for bitrate_data in bitrate_info_list:
        play_addr = bitrate_data.get("PlayAddr", {})
        url_list = play_addr.get("UrlList")
        # if no urls are available, skip this bitrate gng
        if not url_list:
            continue

        # quality string
        height = play_addr.get("Height")
        width = play_addr.get("Width")
        codec_type = bitrate_data.get("CodecType", "unknown")
        # likely video-only (reminder)
        quality_str = f"{height}p ({codec_type})"

        videos.append(Video(
            url=url_list[0],
            quality=quality_str,
            width=width,
            height=height,
            headers={
                'Cookie': '; '.join([f"{k}={v}" for k, v in cookies.items()])
            } if cookies else None
        ))

    # extract video streams
    # the primary playaddr is often a good muxed stream ;P
    primary_download_url = video_info.get("downloadAddr")
    if primary_download_url and not any(v.url == primary_download_url for v in videos):
        videos.append(Video(
            url=primary_download_url,
            quality=f"{video_info.get('height')}p (muxed)", # muxed cuz its the primary download link
            width=video_info.get("width"),
            height=video_info.get("height"),
            headers={
                'Cookie': '; '.join([f"{k}={v}" for k, v in cookies.items()])
            } if cookies else None
        ))

    # remove duplicates and sort videos by height desc.
    unique_videos = {v.url: v for v in videos}.values()
    videos = sorted(list(unique_videos), key=lambda v:v.height or 0, reverse=True)

    # other metadata
    author = author_info.get("nickname", "unknown")
    title = item_struct.get("desc", f"TikTok by {author}")
    thumbnail_url = video_info.get("cover")

    return SodaliteMetadata(
        service="tiktok",
        title=title,
        author=author,
        thumbnail_url=thumbnail_url,
        videos=videos,
        audios=audios
    )

async def fetch_dl(url: str) -> SodaliteMetadata:
    """
    takes in a raw tiktok url, and returns the metadata
    """
    raw_data, cookies = await _get_raw_data(url)
    json_data = _extract_json_from_raw_data(raw_data)
    metadata = _parse_metadata_from_json(json_data, cookies)
    return metadata
