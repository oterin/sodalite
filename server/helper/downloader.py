"""
sodalite downloader - handles downloading and merging with ffmpeg
"""

import os
import asyncio
import aiohttp
import tempfile
import subprocess
import concurrent.futures
from typing import Optional, Tuple
from server.models.metadata import SodaliteMetadata, Video, Audio

async def download_stream(url: str, output_path: str, headers: Optional[dict] = None) -> int:
    """
    download a stream to a file and return bytes downloaded
    """
    headers = headers or {}
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    total_bytes = 0
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()

            with open(output_path, 'wb') as file:
                async for chunk in response.content.iter_chunked(8192):
                    file.write(chunk)
                    total_bytes += len(chunk)

    return total_bytes

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

    # select video
    if metadata.videos:
        if video_quality:
            # try to find exact match
            for v in metadata.videos:
                if v.quality == video_quality:
                    video = v
                    break

        # if no match or no preference, use best (first in sorted list)
        if not video:
            video = metadata.videos[0]

    # select audio
    if metadata.audios:
        if audio_quality:
            # try to find exact match
            for a in metadata.audios:
                if a.quality == audio_quality:
                    audio = a
                    break

        # if no match or no preference, use best
        if not audio:
            audio = metadata.audios[0]

    return video, audio

async def download_and_merge(
    metadata: SodaliteMetadata,
    video_quality: Optional[str] = None,
    audio_quality: Optional[str] = None,
    output_format: str = "mp4",
    output_dir: str = None,
    download_mode: str = "default"
) -> str:
    """
    download video and audio streams, merge them with ffmpeg, and inject metadata
    """
    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("ffmpeg is not installed or not in PATH. Please install ffmpeg.")

    if output_dir is None:
        # Use system temp for final output if not specified, but intermediate files will be in a dedicated safe temp dir
        output_dir = tempfile.gettempdir()

    # Use a temporary directory for intermediate files to ensure they are cleaned up
    with tempfile.TemporaryDirectory(prefix="sodalite_") as temp_dir:
        # create unique filenames for intermediate files in the temp directory
        base_name = f"{metadata.service}_{hash(metadata.title)}"
        video_path = os.path.join(temp_dir, f"{base_name}_video.tmp")
        audio_path = os.path.join(temp_dir, f"{base_name}_audio.tmp")

        # final output path remains in the user-specified or default output_dir
        output_path = os.path.join(output_dir, f"{base_name}_final.{output_format}")

        # get best streams
        video, audio = get_best_streams(metadata, video_quality, audio_quality)

        if download_mode == "video_only":
            audio = None
        elif download_mode == "audio_only":
            video = None

        if not video and not audio:
            raise ValueError("no video or audio streams available")

        # download streams and track bandwidth
        download_tasks = []
        if video:
            download_tasks.append(download_stream(str(video.url), video_path, video.headers))
        if audio:
            download_tasks.append(download_stream(str(audio.url), audio_path, audio.headers))

        results = await asyncio.gather(*download_tasks)
        total_downloaded_bytes = sum(results) if results else 0

        # track bandwidth usage
        if total_downloaded_bytes > 0:
            from server.main import stats
            await stats.add_bandwidth(total_downloaded_bytes)
            print(f"Downloaded {total_downloaded_bytes} bytes for processing")

        # prepare ffmpeg command
        ffmpeg_cmd = ["ffmpeg", "-y"]  # -y to overwrite

        # add inputs
        if video and os.path.exists(video_path):
            ffmpeg_cmd.extend(["-i", video_path])
        if audio and os.path.exists(audio_path):
            ffmpeg_cmd.extend(["-i", audio_path])

        # if we have both video and audio, merge them
        if video and audio and os.path.exists(video_path) and os.path.exists(audio_path):
            ffmpeg_cmd.extend(["-c:v", "copy"])

            # Smart audio codec selection to avoid transcoding
            if (output_format in ('mp4', 'm4a') and audio.codec and 'aac' in audio.codec.lower()) or \
               (output_format == 'webm' and audio.codec and ('opus' in audio.codec.lower() or 'vorbis' in audio.codec.lower())):
                ffmpeg_cmd.extend(["-c:a", "copy"])
            elif output_format == 'webm':
                ffmpeg_cmd.extend(["-c:a", "libopus"])  # webm requires opus or vorbis
            else:
                ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k"]) # default to aac for mp4/m4a
        elif video and os.path.exists(video_path):
            # video only
            ffmpeg_cmd.extend(["-c:v", "copy"])
        elif audio and os.path.exists(audio_path):
            # audio only
            # Optimize to copy codec if compatible to save resources
            if (output_format in ["m4a", "mp4"] and audio.codec and "aac" in audio.codec.lower()) or \
               (output_format == "opus" and audio.codec and "opus" in audio.codec.lower()):
                ffmpeg_cmd.extend(["-c:a", "copy"])
            elif output_format == "mp3":
                ffmpeg_cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"]) # vbr mp3
            elif output_format == "flac":
                ffmpeg_cmd.extend(["-c:a", "flac"])
            elif output_format == "wav":
                ffmpeg_cmd.extend(["-c:a", "pcm_s16le"])
            elif output_format == "opus":
                ffmpeg_cmd.extend(["-c:a", "libopus"])
            else: # for m4a, etc.
                ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        # add metadata
        metadata_args = []
        if metadata.title:
            metadata_args.extend(["-metadata", f"title={metadata.title}"])
        if metadata.author:
            metadata_args.extend(["-metadata", f"artist={metadata.author}"])
        metadata_args.extend([
            "-metadata", f"comment=Downloaded with sodalite from {metadata.service}",
            "-metadata", f"encoder=sodalite"
        ])

        ffmpeg_cmd.extend(metadata_args)

        # output format specific options
        if output_format == "mp4":
            ffmpeg_cmd.extend(["-movflags", "+faststart"])  # optimize for streaming

        # add output
        ffmpeg_cmd.append(output_path)

        # run ffmpeg using thread executor for Windows compatibility
        def run_ffmpeg():
            return subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True
            )

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, run_ffmpeg)

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        return output_path

async def merge_existing_files(
    video_path: Optional[str],
    audio_path: Optional[str],
    output_path: str,
    metadata: Optional[SodaliteMetadata] = None
) -> None:
    """
    merge existing video and audio files with metadata injection
    """
    if not video_path and not audio_path:
        raise ValueError("at least one input file required")

    ffmpeg_cmd = ["ffmpeg", "-y"]

    # add inputs
    if video_path:
        ffmpeg_cmd.extend(["-i", video_path])
    if audio_path:
        ffmpeg_cmd.extend(["-i", audio_path])

    # codec settings
    if video_path and audio_path:
        ffmpeg_cmd.extend(["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"])
    else:
        ffmpeg_cmd.extend(["-c", "copy"])

    # add metadata if provided
    if metadata:
        if metadata.title:
            ffmpeg_cmd.extend(["-metadata", f"title={metadata.title}"])
        if metadata.author:
            ffmpeg_cmd.extend(["-metadata", f"artist={metadata.author}"])

    ffmpeg_cmd.append(output_path)

    # run ffmpeg using thread executor
    def run_ffmpeg():
        return subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True
        )

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, run_ffmpeg)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
