"""
sodalite service for instagram reels
"""

from server.helper.errors import InstagramReelsError
from server.models.metadata import SodaliteMetadata, Video, Audio
from typing import List, Optional
import aiohttp
import re
import json
import xml.etree.ElementTree as ET
import html

async def _get_raw_data(url: str) -> str:
    """fetches the raw html from the instagram reels url"""
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
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if not response.ok:
                raise InstagramReelsError(f"failed to fetch data from {url}")
            return await response.text(encoding='utf-8', errors='ignore')

def _extract_json_from_raw_data(raw_data: str) -> dict:
    """extracts the main json data blob from the raw html"""
    pattern = r'<script type="application/json"[^>]*data-sjs[^>]*>(.*?)</script>'
    matches = re.findall(pattern, raw_data, re.DOTALL)

    if not matches:
        raise InstagramReelsError("could not find any data-sjs json script tags in the response")

    for match_content in matches:
        if '"video_dash_manifest"' in match_content:
            try:
                return json.loads(match_content)
            except json.JSONDecodeError:
                continue

    raise InstagramReelsError("could not find the correct media data json in any of the script tags")

def _find_media_data(data: any) -> Optional[dict]:
    """recursively search for the main media data blob in the json"""
    if isinstance(data, dict):
        required_keys = ['video_dash_manifest', 'owner', 'image_versions2', 'caption', 'pk']
        if all(key in data for key in required_keys):
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
        raise InstagramReelsError("could not find media data in json structure")

    videos: List[Video] = []
    audios: List[Audio] = []

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
                        videos.append(Video(
                            url=url,
                            quality=f"{rep.get('height')}p",
                            width=int(rep.get('width', 0)),
                            height=int(rep.get('height', 0))
                        ))
                    elif content_type == 'audio':
                        audios.append(Audio(
                            url=url,
                            quality=f"{bandwidth // 1000}kbps"
                        ))
        except ET.ParseError as e:
            print(f"Warning: Failed to parse XML manifest. Error: {e}")
            pass

    author = media_data.get("owner", {}).get("username", "unknown")

    caption_node = media_data.get("caption")
    title = caption_node.get("text").split('\n')[0] if caption_node and caption_node.get("text") else f"Instagram Reel by {author}"

    thumbnail_url = media_data.get("image_versions2", {}).get("candidates", [{}])[0].get("url")

    return SodaliteMetadata(
        service="instagram",
        title=title,
        author=author,
        thumbnail_url=thumbnail_url,
        videos=videos,
        audios=audios
    )

async def fetch_dl(url: str) -> SodaliteMetadata:
    """takes in a raw instagram reels url, and returns the metadata"""
    raw_data = await _get_raw_data(url)
    json_data = _extract_json_from_raw_data(raw_data)
    metadata = _parse_metadata_from_json(json_data)
    return metadata
