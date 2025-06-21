"""
sodalite downloader - handles downloading and merging with ffmpeg
"""

import os
import asyncio
import tempfile
import subprocess
import unicodedata
import re
from typing import Optional, Tuple, Callable
from server.models.metadata import SodaliteMetadata, Video, Audio


def sanitize_filename(filename: str) -> str:
    """
    sanitizes a filename to be safe for all operating systems.
    - removes special characters
    - normalizes unicode
    - replaces spaces with underscores
    - limits length to 200 characters
    """
    filename = unicodedata.normalize('NFKD', filename).encode(
        'ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^\w\s-]', '', filename).strip()
    filename = re.sub(r'[-\s]+', '_', filename)
    return filename[:200]


async def download_stream(url: str, output_path: str, headers: Optional[dict] = None) -> int:
    """
    download a stream to a file and return bytes downloaded
    """
    import aiohttp
    print(f"DEBUG: Attempting to download stream from: {url[:100]}...")
    headers = headers or {}
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    print(f"DEBUG: Using headers: {list(headers.keys())}")

    downloaded_bytes = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=60) as response:
                print(
                    f"DEBUG: Received HTTP status: {response.status} for URL: {url[:100]}...")
                response.raise_for_status()
                with open(output_path, 'wb') as file:
                    async for chunk in response.content.iter_chunked(8192):
                        file.write(chunk)
                        downloaded_bytes += len(chunk)
        print(
            f"DEBUG: Successfully downloaded {downloaded_bytes} bytes to {os.path.basename(output_path)}")
    except Exception as e:
        print(f"ERROR: Failed to download stream {url[:100]}...: {e}")
        return 0

    return downloaded_bytes


def get_best_streams(
    metadata: SodaliteMetadata,
    video_quality: Optional[str] = None,
    audio_quality: Optional[str] = None
) -> Tuple[Optional[Video], Optional[Audio]]:
    """
    select the best video and audio streams based on quality preferences
    """
    video = None
    audio = None

    if metadata.videos:
        if video_quality:
            for v in metadata.videos:
                if v.quality == video_quality:
                    video = v
                    break
        if not video:
            video = metadata.videos[0]

    if metadata.audios:
        if audio_quality:
            for a in metadata.audios:
                if a.quality == audio_quality:
                    audio = a
                    break
        if not audio:
            audio = metadata.audios[0]

    return video, audio


async def download_and_merge(
    metadata: SodaliteMetadata,
    video_quality: Optional[str] = None,
    audio_quality: Optional[str] = None,
    output_format: str = "mp4",
    output_dir: str = None,
    download_mode: str = "default",
    task_id: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[str, int]:
    """
    download video and audio streams, merge them with ffmpeg, and inject metadata
    """
    try:
        subprocess.run(["ffmpeg", "-version"],
                       capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError(
            "ffmpeg is not installed or not in PATH. please install ffmpeg.")

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    total_downloaded_bytes = 0

    with tempfile.TemporaryDirectory(prefix="sodalite_") as temp_dir:
        base_filename = sanitize_filename(
            f"{metadata.title}_{metadata.author}")
        output_filename = f"{base_filename}.{output_format}"
        output_path = os.path.join(output_dir, output_filename)

        video_path = os.path.join(
            temp_dir, f"{hash(metadata.title)}_video.tmp")
        audio_path = os.path.join(
            temp_dir, f"{hash(metadata.title)}_audio.tmp")

        video, audio = get_best_streams(
            metadata, video_quality, audio_quality)

        if download_mode == "video_only":
            audio = None
            print("DEBUG: Download mode is 'video_only'. Ignoring audio stream.")
        elif download_mode == "audio_only":
            video = None
            print("DEBUG: Download mode is 'audio_only'. Ignoring video stream.")

        if not video and not audio:
            raise ValueError("no video or audio streams available")

        print(
            f"DEBUG: Selected video stream: {video.quality if video else 'None'}")
        print(
            f"DEBUG: Selected audio stream: {audio.quality if audio else 'None'}")

        if progress_callback:
            progress_callback("downloading")

        download_tasks = []
        if video and video.url:
            print(
                f"DEBUG: Adding video download task for quality '{video.quality}'.")
            download_tasks.append(download_stream(
                str(video.url), video_path, video.headers))
        if audio and audio.url:
            print(
                f"DEBUG: Adding audio download task for quality '{audio.quality}'.")
            download_tasks.append(download_stream(
                str(audio.url), audio_path, audio.headers))

        if download_tasks:
            results = await asyncio.gather(*download_tasks)
            total_downloaded_bytes = sum(results)
            print(
                f"DEBUG: Download tasks finished. Total bytes downloaded: {total_downloaded_bytes}")
            if any(r == 0 for r in results):
                raise RuntimeError("one or more streams failed to download")

        if progress_callback:
            progress_callback("processing")

        ffmpeg_cmd = ["ffmpeg", "-y"]
        if video:
            ffmpeg_cmd.extend(["-i", video_path])
        if audio:
            ffmpeg_cmd.extend(["-i", audio_path])

        if video:
            if output_format == "webm":
                ffmpeg_cmd.extend(["-c:v", "libvpx-vp9"])
            else:
                ffmpeg_cmd.extend(["-c:v", "copy"])
        if audio:
            if output_format == "webm":
                ffmpeg_cmd.extend(["-c:a", "libopus"])
            elif output_format == "mp3":
                ffmpeg_cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
            else:
                ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        metadata_args = [
            "-metadata", f"comment=Downloaded with sodalite from {metadata.service}",
            "-metadata", f"encoder=sodalite"
        ]
        if metadata.title:
            metadata_args.extend(["-metadata", f"title={metadata.title}"])
        if metadata.author:
            metadata_args.extend(["-metadata", f"artist={metadata.author}"])
        ffmpeg_cmd.extend(metadata_args)

        if output_format == "mp4":
            ffmpeg_cmd.extend(["-movflags", "+faststart"])

        ffmpeg_cmd.append(output_path)

        print(f"DEBUG: Executing FFmpeg command: {' '.join(ffmpeg_cmd)}")

        def run_ffmpeg_sync():
            try:
                process = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                print(
                    f"DEBUG: FFmpeg process finished with return code {process.returncode}.")
                if process.returncode != 0:
                    print(f"ERROR: FFmpeg stderr:\n{process.stderr}")
                return process.returncode, process.stderr
            except subprocess.TimeoutExpired:
                print("ERROR: FFmpeg process timed out after 5 minutes.")
                return 1, "Processing timeout"
            except Exception as e:
                print(
                    f"ERROR: An unexpected error occurred during FFmpeg execution: {e}")
                return 1, f"Execution error: {str(e)}"

        loop = asyncio.get_event_loop()
        returncode, stderr = await loop.run_in_executor(None, run_ffmpeg_sync)

        if returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr}")

        if progress_callback:
            progress_callback("completed")
        return output_path, total_downloaded_bytes
