"""
sodalite downloader - handles downloading and merging with ffmpeg
"""

import os
import asyncio
import aiohttp
import tempfile
import subprocess
import concurrent.futures
from typing import Optional, Tuple, Callable
from server.models.metadata import SodaliteMetadata, Video, Audio
import time
import re

async def download_stream(
    url: str,
    output_path: str,
    headers: Optional[dict] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    download a stream to a file and return bytes downloaded
    """
    headers = headers or {}
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    total_bytes = 0
    downloaded_bytes = 0

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()

            content_length = response.headers.get('Content-Length')
            if content_length:
                total_bytes = int(content_length)

            with open(output_path, 'wb') as file:
                async for chunk in response.content.iter_chunked(8192):
                    file.write(chunk)
                    downloaded_bytes += len(chunk)

                    if progress_callback and total_bytes > 0:
                        progress_callback(downloaded_bytes, total_bytes)

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
) -> str:
    """
    download video and audio streams, merge them with ffmpeg, and inject metadata
    """
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError("ffmpeg is not installed or not in PATH. please install ffmpeg.")

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    with tempfile.TemporaryDirectory(prefix="sodalite_") as temp_dir:
        base_name = f"{metadata.service}_{hash(metadata.title)}"
        video_path = os.path.join(temp_dir, f"{base_name}_video.tmp")
        audio_path = os.path.join(temp_dir, f"{base_name}_audio.tmp")
        output_path = os.path.join(output_dir, f"{base_name}_final.{output_format}")

        video, audio = get_best_streams(metadata, video_quality, audio_quality)

        if download_mode == "video_only":
            audio = None
        elif download_mode == "audio_only":
            video = None

        if not video and not audio:
            raise ValueError("no video or audio streams available")

        total_expected_size = 0
        if video:
            async with aiohttp.ClientSession() as session:
                async with session.head(str(video.url), headers=video.headers or {}) as resp:
                    if 'content-length' in resp.headers:
                        total_expected_size += int(resp.headers['content-length'])
        if audio:
            async with aiohttp.ClientSession() as session:
                async with session.head(str(audio.url), headers=audio.headers or {}) as resp:
                    if 'content-length' in resp.headers:
                        total_expected_size += int(resp.headers['content-length'])

        video_downloaded = 0
        audio_downloaded = 0

        def update_progress(downloaded, total, is_video):
            if progress_callback:
                progress_callback("downloading")

        download_tasks = []
        if video:
            download_tasks.append(download_stream(str(video.url), video_path, video.headers, lambda d, t: update_progress(d, t, True)))
        if audio:
            download_tasks.append(download_stream(str(audio.url), audio_path, audio.headers, lambda d, t: update_progress(d, t, False)))

        await asyncio.gather(*download_tasks)

        if progress_callback:
            progress_callback("processing")

        ffmpeg_cmd = ["ffmpeg", "-y", "-progress", "pipe:1", "-nostats"]
        if video:
            ffmpeg_cmd.extend(["-i", video_path])
        if audio:
            ffmpeg_cmd.extend(["-i", audio_path])

        # codec selection
        if video:
            if output_format == "webm":
                ffmpeg_cmd.extend(["-c:v", "libvpx-vp9"])
            else:
                ffmpeg_cmd.extend(["-c:v", "copy"])
        if audio:
            if output_format == "webm":
                ffmpeg_cmd.extend(["-c:a", "libopus"])
            else:
                ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # Metadata injection (from original, simplified prompt missed this but it's good to keep)
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

        def run_ffmpeg_sync():
            try:
                print("starting ffmpeg process...")
                process = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )

                print(f"ffmpeg finished with return code {process.returncode}")
                return process.returncode, process.stderr

            except subprocess.TimeoutExpired:
                print("ffmpeg process timed out")
                return 1, "Processing timeout"
            except Exception as e:
                print(f"ffmpeg execution error: {e}")
                return 1, f"Execution error: {str(e)}"

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            returncode, stderr = await loop.run_in_executor(executor, run_ffmpeg_sync)

        if returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr}")

        if progress_callback:
            progress_callback("completed")
        return output_path
