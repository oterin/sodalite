"""
YouTube handler using yt-dlp Python library directly.
Simple and reliable approach using the yt-dlp library instead of subprocess.
"""

import asyncio
from typing import List, Optional, Dict, Any
import re
import yt_dlp

# Import the shared models
from server.helper.errors import YouTubeError
from server.models.metadata import Video, Audio, SodaliteMetadata

def create_ytdl_options() -> Dict[str, Any]:
    """Create yt-dlp options for extraction."""
    return {
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
    }

def extract_formats_from_ytdl_info(info: Dict[str, Any]) -> tuple[List[Video], List[Audio]]:
    """Extract video and audio formats from yt-dlp info dict."""
    videos = []
    audios = []

    formats = info.get('formats', [])

    for fmt in formats:
        format_url = fmt.get('url')
        if not format_url:
            continue

        # Check format type
        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')
        format_note = fmt.get('format_note', '')
        quality = fmt.get('quality', 0)

        if vcodec != 'none' and acodec == 'none':
            # Video-only stream
            height = fmt.get('height')
            width = fmt.get('width')
            fps = fmt.get('fps')

            # Build quality string
            quality_str = format_note or f"{height}p" if height else "unknown"
            if fps and fps > 30:
                quality_str += f"{fps}"

            # Add format info if available
            ext = fmt.get('ext', '')
            if ext:
                quality_str += f" ({ext})"

            videos.append(Video(
                url=format_url,
                quality=quality_str,
                width=width,
                height=height
            ))

        elif acodec != 'none' and vcodec == 'none':
            # Audio-only stream
            abr = fmt.get('abr')
            asr = fmt.get('asr')
            ext = fmt.get('ext', '')

            # Build quality string
            if abr:
                quality_str = f"{int(abr)}kbps"
            elif asr:
                quality_str = f"{asr}Hz"
            else:
                quality_str = format_note or "unknown"

            if ext:
                quality_str += f" ({ext})"

            audios.append(Audio(
                url=format_url,
                quality=quality_str
            ))

        elif vcodec != 'none' and acodec != 'none':
            # Combined video+audio stream
            height = fmt.get('height')
            width = fmt.get('width')
            ext = fmt.get('ext', '')

            quality_str = format_note or f"{height}p" if height else "unknown"
            quality_str += " (muxed)"

            if ext:
                quality_str += f" ({ext})"

            videos.append(Video(
                url=format_url,
                quality=quality_str,
                width=width,
                height=height
            ))

    # If no formats found, try to get the best single format
    if not videos and not audios:
        url = info.get('url')
        if url:
            height = info.get('height')
            width = info.get('width')
            ext = info.get('ext', '')
            format_note = info.get('format', '')

            quality_str = format_note or f"{height}p" if height else "best"
            if ext:
                quality_str += f" ({ext})"

            videos.append(Video(
                url=url,
                quality=quality_str,
                width=width,
                height=height
            ))

    # Sort formats by quality (highest first)
    videos.sort(key=lambda v: (v.height or 0, v.width or 0), reverse=True)

    # Sort audio by bitrate (extract number from quality string)
    def extract_bitrate(quality: str) -> int:
        match = re.search(r'(\d+)kbps', quality)
        return int(match.group(1)) if match else 0

    audios.sort(key=lambda a: extract_bitrate(a.quality), reverse=True)

    return videos, audios

def extract_metadata_from_ytdl_info(info: Dict[str, Any]) -> tuple[str, str, Optional[str]]:
    """Extract metadata from yt-dlp info dict."""
    title = info.get('title', 'Unknown Title')
    uploader = info.get('uploader', info.get('channel', 'Unknown Author'))

    # Get the best thumbnail
    thumbnails = info.get('thumbnails', [])
    thumbnail_url = None

    if thumbnails:
        # Sort by resolution and get the best one
        sorted_thumbnails = sorted(
            thumbnails,
            key=lambda t: (t.get('width', 0) * t.get('height', 0), t.get('preference', 0)),
            reverse=True
        )
        thumbnail_url = sorted_thumbnails[0].get('url')

    return title, uploader, thumbnail_url

async def fetch_dl(url: str) -> SodaliteMetadata:
    """
    Fetch YouTube video metadata and stream URLs using yt-dlp library.
    """

    try:
        # Run yt-dlp extraction in executor to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_with_ytdlp_sync, url)

        # Extract formats and metadata
        videos, audios = extract_formats_from_ytdl_info(info)
        title, author, thumbnail_url = extract_metadata_from_ytdl_info(info)

        return SodaliteMetadata(
            service="youtube",
            title=title,
            author=author,
            thumbnail_url=thumbnail_url,
            videos=videos,
            audios=audios
        )

    except Exception as e:
        raise YouTubeError(f"Extraction failed: {str(e)}")

def _extract_with_ytdlp_sync(url: str) -> Dict[str, Any]:
    """Extract video info using yt-dlp synchronously."""
    ytdl_opts = create_ytdl_options()

    try:
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(url, download=False)

            if not info:
                raise YouTubeError("No video information could be extracted")

            # Handle playlist case - get first video
            if 'entries' in info:
                entries = list(info['entries'])
                if not entries:
                    raise YouTubeError("Playlist is empty")
                info = entries[0]

            return info

    except yt_dlp.DownloadError as e:
        error_msg = str(e).lower()

        if 'private video' in error_msg:
            raise YouTubeError("Video is private")
        elif 'video unavailable' in error_msg or 'not available' in error_msg:
            raise YouTubeError("Video is unavailable")
        elif 'age-restricted' in error_msg or 'sign in' in error_msg:
            raise YouTubeError("Video is age-restricted or requires sign-in")
        elif 'copyright' in error_msg:
            raise YouTubeError("Video blocked due to copyright")
        elif 'region' in error_msg or 'country' in error_msg:
            raise YouTubeError("Video not available in your region")
        else:
            raise YouTubeError(f"Download error: {str(e)}")

    except Exception as e:
        raise YouTubeError(f"Unexpected error: {str(e)}")

def get_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL using yt-dlp."""
    try:
        ytdl_opts = create_ytdl_options()
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
            return info.get('id') if info else None
    except Exception:
        return None
