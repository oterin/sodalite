"""
youtube handler using yt-dlp python library directly.
simple and reliable approach using the yt-dlp library instead of subprocess.
"""
import asyncio
from typing import List, Optional, Dict, Any
import re
import os
import time
import yt_dlp
import logging
import traceback

from server.helper.errors import YouTubeError
from server.models.metadata import Video, Audio, SodaliteMetadata

logger = logging.getLogger(__name__)


def create_ytdl_options() -> Dict[str, Any]:
    """create yt-dlp options for extraction."""
    print("DEBUG: Creating yt-dlp options...")
    options = {
        'quiet': True,
        'no_warnings': False,
        'extract_flat': False,
        'skip_download': True,
        'format': 'best[height<=?2160][protocol!*=m3u8]',
        'extractor_args': {
            'youtube': ['player_client=default,ios']
        },
        'ignoreerrors': False,
        'age_limit': None,
        'cookiesfrombrowser': None,
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'socket_timeout': 20,
    }

    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    if os.path.exists(cookies_path):
        print(f"DEBUG: Found cookies file at {cookies_path}. Adding to options.")
        options['cookiefile'] = cookies_path
    else:
        print("DEBUG: No cookies file found.")

    return options


def extract_formats_from_ytdl_info(info: Dict[str, Any]) -> tuple[List[Video], List[Audio]]:
    """extract and de-duplicate video and audio formats from yt-dlp info dict."""
    print("DEBUG: Extracting formats from yt-dlp info...")
    unique_videos: Dict[str, Video] = {}
    unique_audios: Dict[str, Audio] = {}

    formats = info.get('formats', [])
    print(f"DEBUG: Found {len(formats)} formats to process.")

    for i, fmt in enumerate(formats):
        if not isinstance(fmt, dict):
            print(f"DEBUG: Skipping format #{i+1} because it is not a dictionary.")
            continue

        format_url = fmt.get('url')
        vcodec = fmt.get('vcodec', 'none')

        if not format_url or 'av01' in vcodec:
            print(f"DEBUG: Skipping format #{i+1} due to no URL or AV1 codec.")
            continue

        acodec = fmt.get('acodec', 'none')

        if vcodec != 'none':
            height = fmt.get('height')
            if not height:
                continue

            quality_key = f"{height}p"
            if fmt.get('fps') and fmt.get('fps') > 30:
                quality_key += f"{int(fmt.get('fps'))}"

            if quality_key not in unique_videos:
                print(f"DEBUG: Adding video format: {quality_key}")
                unique_videos[quality_key] = Video(
                    url=format_url,
                    quality=quality_key,
                    width=fmt.get('width'),
                    height=height,
                    codec=vcodec,
                    headers=fmt.get('http_headers')
                )

        elif acodec != 'none' and vcodec == 'none':
            abr = fmt.get('abr')
            if not abr:
                continue

            quality_key = f"{int(abr)}kbps"
            if quality_key not in unique_audios:
                print(f"DEBUG: Adding audio format: {quality_key}")
                unique_audios[quality_key] = Audio(
                    url=format_url,
                    quality=quality_key,
                    codec=acodec,
                    headers=fmt.get('http_headers')
                )

    videos = sorted(list(unique_videos.values()), key=lambda v: (
        v.height or 0), reverse=True)
    audios = sorted(list(unique_audios.values()), key=lambda a: int(
        a.quality.replace('kbps', '')), reverse=True)
    print(f"DEBUG: Extracted {len(videos)} unique video formats and {len(audios)} unique audio formats.")
    return videos, audios


def extract_metadata_from_ytdl_info(info: Dict[str, Any]) -> tuple[str, str, Optional[str]]:
    """extract metadata from yt-dlp info dict."""
    print("DEBUG: Extracting metadata (title, author, thumbnail)...")
    title = info.get('title', 'unknown title')
    uploader = info.get('uploader', info.get('channel', 'unknown author'))
    thumbnails = info.get('thumbnails', [])
    thumbnail_url = None

    if thumbnails:
        sorted_thumbnails = sorted(
            thumbnails,
            key=lambda t: (t.get('width', 0) *
                           t.get('height', 0), t.get('preference', 0)),
            reverse=True
        )
        thumbnail_url = sorted_thumbnails[0].get('url')

    print(f"DEBUG: Extracted metadata - Title: {title[:30]}..., Author: {uploader}, Thumbnail URL: {'Yes' if thumbnail_url else 'No'}")
    return title, uploader, thumbnail_url


async def fetch_dl(url: str) -> SodaliteMetadata:
    """
    fetch youtube video metadata and stream urls using yt-dlp library.
    """
    print(f"DEBUG: Starting fetch_dl for URL: {url}")
    try:
        loop = asyncio.get_running_loop()
        info = await asyncio.wait_for(
            loop.run_in_executor(None, _extract_with_ytdlp_sync, url),
            timeout=60.0
        )

        if not info:
            print("ERROR: _extract_with_ytdlp_sync returned None.")
            raise YouTubeError("failed to extract video information.")

        print("DEBUG: Successfully extracted info dict from yt-dlp.")
        videos, audios = extract_formats_from_ytdl_info(info)
        title, author, thumbnail_url = extract_metadata_from_ytdl_info(info)

        from pydantic import HttpUrl, ValidationError
        valid_thumbnail_url = None
        if thumbnail_url:
            try:
                valid_thumbnail_url = HttpUrl(thumbnail_url)
            except (ValidationError, ValueError, TypeError):
                print(f"WARNING: Invalid thumbnail URL format: {thumbnail_url}")
                valid_thumbnail_url = None

        print("DEBUG: Successfully created SodaliteMetadata object.")
        return SodaliteMetadata(
            service="youtube",
            title=title,
            author=author,
            thumbnail_url=valid_thumbnail_url,
            videos=videos,
            audios=audios
        )
    except asyncio.TimeoutError:
        print("ERROR: Metadata extraction timed out after 60 seconds.")
        raise YouTubeError("metadata extraction timed out")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in fetch_dl: {e}")
        # Re-raise as YouTubeError to be caught by the main handler
        raise YouTubeError(f"extraction failed: unexpected error: {e}")


def _extract_with_ytdlp_sync(url: str) -> Optional[Dict[str, Any]]:
    """extract video info using yt-dlp synchronously with retries."""
    print("DEBUG: Starting synchronous extraction with yt-dlp...")
    ytdl_opts = create_ytdl_options()
    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        print(f"DEBUG: yt-dlp extraction attempt #{attempt + 1}")
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception:
                    print("ERROR: Exception during ydl.extract_info():")
                    traceback.print_exc()
                    raise

                if not info:
                    print(f"WARNING: yt-dlp attempt #{attempt + 1} returned no info.")
                    continue

                if 'entries' in info:
                    print("DEBUG: Playlist detected. Extracting first entry.")
                    entries = list(info['entries'])
                    if not entries:
                        raise YouTubeError("playlist is empty")
                    info = entries[0]

                print(f"DEBUG: yt-dlp attempt #{attempt + 1} successful.")
                return info

        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            print(f"DEBUG: yt-dlp DownloadError on attempt #{attempt + 1}: {error_msg}")

            if '429' in error_msg and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(
                    f"DEBUG: HTTP 429 received. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue

            error_map = {
                'private video': "video is private",
                'video unavailable': "video is unavailable",
                'not available': "video is unavailable",
                'age-restricted': "video is age-restricted or requires sign-in",
                'sign in': "video is age-restricted or requires sign-in",
                'copyright': "video blocked due to copyright",
                'region': "video not available in your region",
                'country': "video not available in your region"
            }
            for key, msg in error_map.items():
                if key in error_msg:
                    raise YouTubeError(msg)

            # If no specific error matched, raise a generic one for the last attempt
            if attempt == max_retries - 1:
                raise YouTubeError(f"download error: {e}")

        except Exception as e:
            print(f"ERROR: An unexpected exception occurred during yt-dlp extraction on attempt #{attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise e # Re-raise the final exception

    print("ERROR: Extraction failed after all retries.")
    return None
