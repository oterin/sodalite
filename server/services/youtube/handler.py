"""
youtube handler using yt-dlp python library directly.
simple and reliable approach using the yt-dlp library instead of subprocess.
"""
import asyncio
from typing import List, Optional, Dict, Any
import re
import os
import random
import time
import yt_dlp
import time
import logging

# import the shared models
from server.helper.errors import YouTubeError
from server.models.metadata import Video, Audio, SodaliteMetadata

logger = logging.getLogger(__name__)

def create_ytdl_options() -> Dict[str, Any]:
    """create yt-dlp options for extraction."""
    options = {
        'quiet': True,
        'no_warnings': False,
        'extract_flat': False,
        'skip_download': True,
        'format': 'best[height<=?2160]',
        'ignoreerrors': False,
        'age_limit': None,
        'cookiesfrombrowser': None,
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'socket_timeout': 20,
    }

    # add cookies.txt if it exists in the same directory (netscape format)
    cookies_path = 'server/services/youtube/cookies.txt'
    if os.path.exists(cookies_path):
        print(f"using cookies from {cookies_path} (netscape format)")
        options['cookiefile'] = cookies_path

    return options

def extract_formats_from_ytdl_info(info: Dict[str, Any]) -> tuple[List[Video], List[Audio]]:
    """extract and de-duplicate video and audio formats from yt-dlp info dict."""

    unique_videos: Dict[str, Video] = {}
    unique_audios: Dict[str, Audio] = {}

    formats = info.get('formats', [])

    for fmt in formats:
        format_url = fmt.get('url')
        # skip problematic formats
        if not format_url or fmt.get('vcodec') == 'av01':
            continue

        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        # video streams (including muxed)
        if vcodec != 'none':
            height = fmt.get('height')
            width = fmt.get('width')
            fps = fmt.get('fps')
            ext = fmt.get('ext')

            if not height: continue

            # create a unique key for this quality
            quality_key = f"{height}p"
            if fps and fps > 30:
                quality_key += f"{int(fps)}"

            # simple quality string
            quality_str = quality_key

            # prioritize mp4 over webm, and non-muxed over muxed for simplicity
            if quality_key not in unique_videos or (ext == 'mp4' and not unique_videos[quality_key].quality.endswith('(video+audio)')):
                unique_videos[quality_key] = Video(
                    url=format_url,
                    quality=quality_str,
                    width=width,
                    height=height
                )

        # audio-only streams
        elif acodec != 'none' and vcodec == 'none':
            abr = fmt.get('abr')
            ext = fmt.get('ext')

            if not abr: continue

            quality_key = f"{int(abr)}kbps"

            # prioritize m4a/mp4a over others
            if quality_key not in unique_audios or (ext == 'm4a'):
                unique_audios[quality_key] = Audio(
                    url=format_url,
                    quality=quality_key
                )

    # convert dicts to lists
    videos = list(unique_videos.values())
    audios = list(unique_audios.values())

    # sort formats by quality (highest first)
    videos.sort(key=lambda v: (v.height or 0), reverse=True)

    def extract_bitrate(quality: str) -> int:
        match = re.search(r'(\d+)kbps', quality)
        return int(match.group(1)) if match else 0

    audios.sort(key=lambda a: extract_bitrate(a.quality), reverse=True)

    return videos, audios

def extract_metadata_from_ytdl_info(info: Dict[str, Any]) -> tuple[str, str, Optional[str]]:
    """extract metadata from yt-dlp info dict."""
    title = info.get('title', 'unknown title')
    uploader = info.get('uploader', info.get('channel', 'unknown author'))

    # get the best thumbnail
    thumbnails = info.get('thumbnails', [])
    thumbnail_url = None

    if thumbnails:
        # sort by resolution and get the best one
        sorted_thumbnails = sorted(
            thumbnails,
            key=lambda t: (t.get('width', 0) * t.get('height', 0), t.get('preference', 0)),
            reverse=True
        )
        thumbnail_url = sorted_thumbnails[0].get('url')

    return title, uploader, thumbnail_url

async def fetch_dl(url: str) -> SodaliteMetadata:
    """
    fetch youtube video metadata and stream urls using yt-dlp library.
    """

    try:
        # run yt-dlp extraction in executor to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_with_ytdlp_sync, url)

        # extract formats and metadata
        videos, audios = extract_formats_from_ytdl_info(info)
        title, author, thumbnail_url = extract_metadata_from_ytdl_info(info)

        # u0927kg2f97: ensure thumbnail_url is none if not a string or not a valid url
        # sodalitemetadata expects thumbnail_url as httpurl | none, so pass none if not a string or not a valid url
        from pydantic import HttpUrl, ValidationError

        valid_thumbnail_url = None
        if thumbnail_url:
            try:
                valid_thumbnail_url = HttpUrl(thumbnail_url)
            except (ValidationError, ValueError, TypeError):
                valid_thumbnail_url = None

        return SodaliteMetadata(
            service="youtube",
            title=title,
            author=author,
            thumbnail_url=valid_thumbnail_url,
            videos=videos,
            audios=audios
        )

    except Exception as e:
        raise YouTubeError(f"extraction failed: {str(e)}")

def _extract_with_ytdlp_sync(url: str) -> Dict[str, Any]:
    """extract video info using yt-dlp synchronously with retries."""
    ytdl_opts = create_ytdl_options()
    max_retries = 3
    base_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                # extract info without downloading
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise YouTubeError("no video information could be extracted")

                # handle playlist case - get first video
                if 'entries' in info:
                    entries = list(info['entries'])
                    if not entries:
                        raise YouTubeError("playlist is empty")
                    info = entries[0]

                return info

        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()

            # check for http 429 and retry with exponential backoff
            if '429' in error_msg and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"youtube handler: http 429 received. retrying in {delay} seconds...")
                time.sleep(delay)
                continue

            # check for other common errors
            if 'private video' in error_msg:
                raise YouTubeError("video is private")
            elif 'video unavailable' in error_msg or 'not available' in error_msg:
                raise YouTubeError("video is unavailable")
            elif 'age-restricted' in error_msg or 'sign in' in error_msg:
                raise YouTubeError("video is age-restricted or requires sign-in")
            elif 'copyright' in error_msg:
                raise YouTubeError("video blocked due to copyright")
            elif 'region' in error_msg or 'country' in error_msg:
                raise YouTubeError("video not available in your region")
            else:
                # if it's the last attempt on a 429 or any other error, raise it
                raise YouTubeError(f"download error: {str(e)}")

        except Exception as e:
            # handle non-download errors
            raise YouTubeError(f"unexpected error: {str(e)}")

    # if all retries fail
    raise YouTubeError("extraction failed after multiple retries due to rate limiting.")


def get_video_id(url: str) -> Optional[str]:
    """extract video id from youtube url using yt-dlp."""
    try:
        ytdl_opts = create_ytdl_options()
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
            return info.get('id') if info else None
    except Exception:
        return None
