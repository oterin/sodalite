"""
sodalite service for instagram
"""

from server.helper.errors import InstagramError
from server.models.metadata import SodaliteMetadata, Video, Audio
from typing import Dict, Optional
import aiohttp
import re
import json
import xml.etree.ElementTree as ET
import asyncio

async def _get_raw_data(url: str, retry_count: int = 3) -> str:
    """fetches the raw html from the instagram url with retry logic"""
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="137.0.7151.104", "Chromium";v="137.0.7151.104", "Not/A)Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"19.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'viewport-width': '150'
    }

    for attempt in range(retry_count):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if not response.ok:
                        if attempt < retry_count - 1:
                            await asyncio.sleep(1)  # Wait 1 second before retry
                            continue
                        raise InstagramError(f"failed to fetch data from {url}")
                    return await response.text(encoding='utf-8', errors='ignore')
        except Exception as e:
            if attempt < retry_count - 1:
                await asyncio.sleep(1)  # Wait 1 second before retry
                continue
            raise InstagramError(f"failed to fetch data from {url}: {str(e)}")

    raise InstagramError(f"failed to fetch data from {url} after {retry_count} attempts")

def _extract_json_from_raw_data(raw_data: str) -> dict:
    """extracts the main json data blob from the raw html"""
    pattern = r'<script type="application/json"[^>]*data-sjs[^>]*>(.*?)</script>'
    matches = re.findall(pattern, raw_data, re.DOTALL)

    if not matches:
        raise InstagramError("could not find any data-sjs json script tags in the response")

    # First try to find a script tag with video_dash_manifest
    for match_content in matches:
        if '"video_dash_manifest"' in match_content:
            try:
                return json.loads(match_content)
            except json.JSONDecodeError:
                continue

    # If that fails, try to parse all script tags and look for media data
    for match_content in matches:
        try:
            parsed_data = json.loads(match_content)
            # Check if this JSON contains media data
            if _find_media_data(parsed_data):
                return parsed_data
        except json.JSONDecodeError:
            continue

    raise InstagramError("could not find the correct media data json in any of the script tags")

def _find_media_data(data: dict) -> Optional[dict]:
    """recursively search for the main media data blob in the json"""
    if isinstance(data, dict):
        # Check for required keys - some might be optional
        required_keys = ['owner', 'pk']
        optional_keys = ['video_dash_manifest', 'image_versions2', 'caption']

        if all(key in data for key in required_keys) and any(key in data for key in optional_keys):
            return data

        for value in data.values():
            found = _find_media_data(value)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = _find_media_data(item)
            if found:
                return found

    return None

def _parse_metadata_from_json(json_data: dict) -> SodaliteMetadata:
    """parses the json data and returns a sodalitemetadata object"""
    media_data = _find_media_data(json_data)
    if not media_data:
        raise InstagramError("could not find media data in json structure")

    unique_videos: Dict[str, Video] = {}
    unique_audios: Dict[str, Audio] = {}

    dash_manifest_xml = media_data.get("video_dash_manifest")
    if dash_manifest_xml:
        try:
            root = ET.fromstring(dash_manifest_xml)
            ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

            for aset in root.findall('.//mpd:AdaptationSet', ns):
                content_type = aset.get('contentType')
                for rep in aset.findall('.//mpd:Representation', ns):
                    base_url_node = rep.find('mpd:BaseURL', ns)
                    if base_url_node is None or not base_url_node.text: continue

                    url = base_url_node.text
                    bandwidth = int(rep.get('bandwidth', 0))

                    if content_type == 'video':
                        height = int(rep.get('height', 0))
                        quality_key = f"{height}p"
                        if quality_key not in unique_videos:
                            unique_videos[quality_key] = Video(
                                url=url,
                                quality=quality_key,
                                width=int(rep.get('width', 0)),
                                height=height
                            )
                    elif content_type == 'audio':
                        quality_key = f"{bandwidth // 1000}kbps"
                        if quality_key not in unique_audios:
                            unique_audios[quality_key] = Audio(
                                url=url,
                                quality=quality_key
                            )
        except ET.ParseError as e:
            print(f"Warning: Failed to parse XML manifest. Error: {e}")
            pass

    videos = sorted(list(unique_videos.values()), key=lambda v: v.height or 0, reverse=True)
    audios = sorted(list(unique_audios.values()), key=lambda a: int(a.quality.replace('kbps', '')), reverse=True)

    author = media_data.get("owner", {}).get("username", "unknown")

    caption_node = media_data.get("caption")
    title = caption_node.get("text").split('\n')[0] if caption_node and caption_node.get("text") else f"Instagram Post by {author}"

    thumbnail_url = media_data.get("image_versions2", {}).get("candidates", [{}])[0].get("url")

    # if no video/audio streams, it's a photo post
    if not videos and not audios and thumbnail_url:
        # create a "video" from the thumbnail for downloading
        photo_video = Video(
            url=thumbnail_url,
            quality="photo",
            width=media_data.get("original_width"),
            height=media_data.get("original_height"),
        )
        videos.append(photo_video)

    return SodaliteMetadata(
        service="instagram",
        title=title,
        author=author,
        thumbnail_url=thumbnail_url,
        videos=videos,
        audios=audios
    )

async def fetch_dl(url: str, retry_count: int = 3) -> SodaliteMetadata:
    """takes in a raw instagram  url, and returns the metadata with retry logic"""
    last_error = None

    for attempt in range(retry_count):
        try:
            raw_data = await _get_raw_data(url)
            json_data = _extract_json_from_raw_data(raw_data)
            metadata = _parse_metadata_from_json(json_data)
            return metadata
        except InstagramError as e:
            last_error = e
            if "could not find the correct media data json" in str(e) or "could not find media data in json structure" in str(e):
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)  # Wait 1 second before retry
                    continue
            raise e
        except Exception as e:
            last_error = e
            if attempt < retry_count - 1:
                await asyncio.sleep(1)  # Wait 1 second before retry
                continue
            raise e

    raise last_error or InstagramError(f"failed to fetch metadata after {retry_count} attempts")
