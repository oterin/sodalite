"""
sodaltie downloader - handles downloading and merging with ffmpeg
"""

import os
import asyncio
import aiohttp
import tempfile
import subprocess
from typing import Optional, Tuple
from server.models.metadata import SodaliteMetadata, Video, Audio

async def download_stream(
    url: str,
    output_path: str,
    headers: Optional[dict] = None,
) -> None:
    """
    download a stream to a file
    """
    headers = headers or {}
    headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

def get_best_streams(
    metadata: SodaliteMetadata,
    video_quality: Optional[str] = None,
    audio_quality: Optional[str] = None
) ->  Tuple[Optional[Video], Optional[Audio]]:
    """
    select the best video and audio streams based on quality preferences
    """
    video = None
    audio = None

    # select video
    if metadata.videos:
        if video_quality:
            # lets try to find an exact match first
            for v in metadata.videos:
                if v.quality == video_quality:
                    video = v
                    break


            # if no match or no preference, let's use the best available
            if not video:
                video = metadata.videos[0]

    # select audio
    if metadata.audios:
        if audio_quality:
            # lets try to find an exact match first
            for a in metadata.audios:
                if a.quality == audio_quality:
                    audio = a
                    break

            # if no match or no preference, let's use the best available
            if not audio:
                audio = metadata.audios[0]

    return video, audio

async def download_and_merge(
    metadata: SodaliteMetadata,
    video_quality: Optional[str] = None,
    audio_quality: Optional[str] = None,
    output_format: str = 'mp4',
    output_dir: str = ''
) -> str:
    """
    download video and audio streams, merge them using ffmpeg, and inject metadata
    """

    # create unique filenames
    base_name = f"{metadata.service}_{hash(metadata.title)}"
    video_path = os.path.join(output_dir, f"{base_name}_video.tmp")
    audio_path = os.path.join(output_dir, f"{base_name}_audio.tmp")
    output_path = os.path.join(output_dir, f"{base_name}_final.{output_format}")

    try:
        # get best streams
        video, audio = get_best_streams(metadata, video_quality, audio_quality)

        if not video and not audio:
            raise ValueError("no video or audio streams available")

        # download streams
        tasks = []
        if video:
            tasks.append(download_stream(str(video.url), video_path, video.headers))
        if audio:
            tasks.append(download_stream(str(audio.url), audio_path, audio.headers))

        # prepare ffmpeg command
        ffmpeg_cmd = ["ffmpeg", "-y"] # -y to overwrite output files

        # add inputs
        if video and os.path.exists(video_path):
            ffmpeg_cmd.extend(["-i", video_path])
        if audio and os.path.exists(audio_path):
            ffmpeg_cmd.extend(["-i", audio_path])

        # if we have both video and audio, we can merge them
        if video and audio and os.path.exists(video_path) and os.path.exists(audio_path):
            ffmpeg_cmd.extend([
                "-c:v", "copy", # copy video codec
                "-c:a", "aac",  # convert audio to aac
                "-b:a", "192k", # audio bitrate
            ])
        elif video and os.path.exists(video_path):
            # video only
            ffmpeg_cmd.extend(["-c:v", "copy"])
        elif audio and os.path.exists(audio_path):
            # audio only
            ffmpeg_cmd.extend(["-c:a", "copy"])

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

        # output format specific options
        if output_format == "mp4":
            ffmpeg_cmd.extend(["-movflags", "+faststart"]) # for better streaming

        # add output
        ffmpeg_cmd.append(output_path)

        # run ffmpeg
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")

        return output_path

    finally:
        # cleanup temporary files
        for path in [video_path, audio_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

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

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    await process.communicate()
