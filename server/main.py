"""
sodalite api server - the main entry point
"""

import os
import tempfile
import hashlib
import json
from datetime import datetime, timedelta
from pydantic.json import pydantic_encoder

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal, List, Dict
import git
import asyncio
import json
import aiofiles
import threading
import time
from contextlib import asynccontextmanager
import copy

from server.helper.detector import detect_service
from server.helper.errors import (
    InstagramReelsError,
    YouTubeError,
    TikTokError
)
from server.models.metadata import SodaliteMetadata, SanitizedSodaliteMetadata
from server.services import (
    instagram_reels,
    youtube,
    tiktok
)
from server.helper.downloader import download_and_merge
import aiohttp

download_semaphore = asyncio.Semaphore(2)
DOWNLOAD_CLEANUP_DELAY_MINUTES = 5
CACHE_DURATION = 30  # seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    print("sodalite server starting up...")
    global cleanup_task
    cleanup_task = asyncio.create_task(cleanup_stuck_tasks())
    yield
    # shutdown
    print("sodalite server shutting down...")
    if cleanup_task and not cleanup_task.done():
        cleanup_task.cancel()

app = FastAPI(
    title="sodalite",
    description="a simple downloader for the web - no ads, no tracking, just downloads",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class DownloadRequest(BaseModel):
    url: HttpUrl

class ProcessRequest(BaseModel):
    url: HttpUrl
    video_quality: Optional[str] = None
    audio_quality: Optional[str] = None
    format: Literal["mp4", "webm", "mkv", "mp3", "m4a", "opus", "flac", "ogg", "wav"] = "mp4"
    download_mode: Literal["default", "video_only", "audio_only"] = "default"

class ProcessResponse(BaseModel):
    task_id: str
    status: Literal["processing", "completed", "failed"]
    download_url: Optional[str] = None
    error: Optional[str] = None
    phase: Optional[Literal["initializing", "downloading", "processing", "completed", "failed"]] = None
    file_size_mb: Optional[float] = None
    video_quality: Optional[str] = None
    audio_quality: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    service: Optional[str] = None

class ServiceInfo(BaseModel):
    name: str
    example_urls: list[str]

class ServicesResponse(BaseModel):
    services: dict[str, ServiceInfo]

TEMP_DIR = tempfile.gettempdir()
DOWNLOAD_DIR = os.path.join(TEMP_DIR, "sodalite_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# global state
tasks: Dict[str, Dict] = {}
task_phases: Dict[str, str] = {}
metadata_cache: Dict[str, Dict] = {}
active_websockets: List[WebSocket] = []
task_websockets: Dict[str, List[WebSocket]] = {}
heartbeat_count: int = 0
stats_broadcast_task: Optional[asyncio.Task] = None
cleanup_task: Optional[asyncio.Task] = None

STATS_FILE = os.path.join(DOWNLOAD_DIR, "sodalite_stats.json")

class Statistics:
    def __init__(self):
        self.total_conversions = 0
        self.total_bandwidth_bytes = 0
        self.load_from_file()

    def load_from_file(self):
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    data = json.load(f)
                    self.total_conversions = data.get('total_conversions', 0)
                    self.total_bandwidth_bytes = data.get('total_bandwidth_bytes', 0)
        except Exception as e:
            print(f"failed to load stats: {e}")

    async def save_to_file(self):
        try:
            data = {
                'total_conversions': self.total_conversions,
                'total_bandwidth_bytes': self.total_bandwidth_bytes,
                'last_updated': datetime.now().isoformat()
            }
            async with aiofiles.open(STATS_FILE, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            print(f"failed to save stats: {e}")

    async def increment_conversion(self):
        self.total_conversions += 1
        await self.save_to_file()

    async def add_bandwidth(self, bytes_count: int):
        self.total_bandwidth_bytes += bytes_count
        await self.save_to_file()

stats = Statistics()
file_cleanup_tasks = {}

async def broadcast_stats():
    # this function is now defined before it's called
    if active_websockets:
        message = json.dumps({
            "type": "stats",
            "heartbeats": heartbeat_count,
            "connected_clients": len(active_websockets),
            "total_conversions": stats.total_conversions,
            "total_bandwidth_mb": round(stats.total_bandwidth_bytes / (1024 * 1024), 2)
        })
        disconnected_websockets = []
        for websocket in active_websockets:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected_websockets.append(websocket)
        for websocket in disconnected_websockets:
            active_websockets.remove(websocket)

async def periodic_stats_broadcast():
    """broadcast stats to all connected websockets every 10 seconds"""
    while True:
        try:
            await asyncio.sleep(10)
            await broadcast_stats()
        except Exception as e:
            print(f"error in periodic stats broadcast: {e}")

def get_cache_key(url: str) -> str:
    """generate cache key from url"""
    return hashlib.md5(url.encode()).hexdigest()

def is_cache_valid(timestamp: float) -> bool:
    """check if cache entry is still valid (30 seconds)"""
    return time.time() - timestamp < 30

def clean_metadata_cache():
    """remove expired cache entries"""
    current_time = time.time()
    expired_keys = [
        key for key, data in metadata_cache.items()
        if current_time - data["timestamp"] > 30
    ]
    for key in expired_keys:
        del metadata_cache[key]

def sanitize_metadata(metadata: dict) -> dict:
    """remove sensitive data like urls and headers from metadata"""
    sanitized = metadata.copy()

    # remove direct urls and headers from videos
    if "videos" in sanitized:
        for video in sanitized["videos"]:
            video.pop("url", None)
            video.pop("headers", None)

    # remove direct urls and headers from audios
    if "audios" in sanitized:
        for audio in sanitized["audios"]:
            audio.pop("url", None)
            audio.pop("headers", None)

    return sanitized

async def cleanup_stuck_tasks():
    """clean up tasks that have been processing for too long"""
    while True:
        try:
            await asyncio.sleep(60)  # check every minute
            current_time = time.time()
            stuck_tasks = []

            for task_id, task_data in tasks.items():
                if task_data.get("status") == "processing":
                    created_at = task_data.get("created_at")
                    if created_at:
                        try:
                            created_time = datetime.fromisoformat(created_at).timestamp()
                            if current_time - created_time > 600:  # 10 minutes
                                stuck_tasks.append(task_id)
                        except:
                            pass

            for task_id in stuck_tasks:
                print(f"cleaning up stuck task: {task_id}")
                tasks[task_id].update({
                    "status": "failed",
                    "error": "task timeout - processing took too long"
                })

            # also clean up metadata cache periodically
            clean_metadata_cache()

        except Exception as e:
            print(f"error in cleanup task: {e}")

def cleanup_file_after_delay(file_path: str, delay_minutes: int = 10):
    def cleanup():
        time.sleep(delay_minutes * 60)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"cleaned up file: {file_path}")
            if file_path in file_cleanup_tasks:
                del file_cleanup_tasks[file_path]
        except Exception as e:
            print(f"error cleaning up file {file_path}: {e}")

    if file_path in file_cleanup_tasks:
        pass

    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()
    file_cleanup_tasks[file_path] = cleanup_thread

SERVICE_HANDLERS = {
    "instagram_reels": instagram_reels.fetch_dl,
    "youtube": youtube.fetch_dl,
    "tiktok": tiktok.fetch_dl
}

SERVICE_ERRORS = {
    "instagram_reels": InstagramReelsError,
    "youtube": YouTubeError,
    "tiktok": TikTokError
}

SERVICE_INFO = {
    "instagram_reels": ServiceInfo(
        name="Instagram Reels",
        example_urls=[
            "https://www.instagram.com/reel/ABC123",
            "https://www.instagram.com/reels/XYZ789"
        ]
    ),
    "youtube": ServiceInfo(
        name="YouTube",
        example_urls=[
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/shorts/abc123"
        ]
    ),
    "tiktok": ServiceInfo(
        name="TikTok",
        example_urls=[
            "https://www.tiktok.com/@user/video/1234567890"
        ]
    )
}

def generate_task_id(url: str) -> str:
    timestamp = datetime.now().isoformat()
    return hashlib.md5(f"{url}{timestamp}".encode()).hexdigest()

def generate_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def is_cache_valid(entry: dict) -> bool:
    """check if cache entry is still valid (within 30 seconds)"""
    if "cached_at" not in entry:
        return False
    cached_time = entry["cached_at"]
    return time.time() - cached_time < CACHE_DURATION

def get_cached_metadata(url: str) -> Optional[SodaliteMetadata]:
    """get cached metadata if available and valid"""
    cache_key = generate_cache_key(url)
    if cache_key in metadata_cache:
        entry = metadata_cache[cache_key]
        if is_cache_valid(entry):
            return entry["metadata"]
        else:
            # remove expired entry
            del metadata_cache[cache_key]
    return None

def cache_metadata(url: str, metadata: SodaliteMetadata):
    """cache metadata for 30 seconds"""
    cache_key = generate_cache_key(url)
    metadata_cache[cache_key] = {
        "metadata": metadata,
        "cached_at": time.time()
    }

def sanitize_metadata_for_response(metadata: SodaliteMetadata) -> dict:
    """remove urls and headers from metadata before sending to client"""
    sanitized = {
        "service": metadata.service,
        "title": metadata.title,
        "author": metadata.author,
        "thumbnail_url": metadata.thumbnail_url,
        "videos": [
            {
                "quality": video.quality,
                "width": video.width,
                "height": video.height,
                "codec": video.codec
            } for video in metadata.videos
        ],
        "audios": [
            {
                "quality": audio.quality,
                "codec": audio.codec
            } for audio in metadata.audios
        ]
    }
    return sanitized

async def process_download_task(
    task_id: str,
    metadata: SodaliteMetadata,
    request: ProcessRequest
):
    loop = asyncio.get_running_loop()

    def phase_callback(phase: str):
        print(f"phase update for {task_id}: {phase}")
        task_phases[task_id] = phase

    async with download_semaphore:
        try:
            print(f"starting download task {task_id}")
            tasks[task_id]["status"] = "processing"
            task_phases[task_id] = "initializing"

            output_path = await download_and_merge(
                metadata=metadata,
                video_quality=request.video_quality,
                audio_quality=request.audio_quality,
                output_format=request.format,
                output_dir=DOWNLOAD_DIR,
                download_mode=request.download_mode,
                task_id=task_id,
                progress_callback=phase_callback
            )

            print(f"download task {task_id} completed successfully")
            file_size_bytes = os.path.getsize(output_path)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
            tasks[task_id].update({
                "status": "completed",
                "download_url": f"/sodalite/download/{task_id}/file",
                "file_path": output_path,
                "completed_at": datetime.now().isoformat(),
                "file_size_mb": file_size_mb
            })

            # ensure final phase is sent
            if phase_callback:
                phase_callback("completed")

            await stats.increment_conversion()

            # schedule file cleanup
            cleanup_file_after_delay(output_path, DOWNLOAD_CLEANUP_DELAY_MINUTES)

        except Exception as e:
            print(f"download task {task_id} failed: {str(e)}")
            tasks[task_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            })
            final_update = {
                "type": "task_status",
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }
            await broadcast_task_update(task_id, final_update)

            import traceback
            traceback.print_exc()

@app.post(
    "/sodalite/download",
    response_model=SanitizedSodaliteMetadata,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "bad request - invalid url or service not supported"
        }
    }
)
async def get_download_info(request: DownloadRequest):
    url_str = str(request.url)

    # check cache first
    cached_metadata = get_cached_metadata(url_str)
    if cached_metadata:
        print(f"using cached metadata for {url_str}")
        return sanitize_metadata_for_response(cached_metadata)

    service = detect_service(url_str)

    if service == "unknown":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported service",
                "service": None
            }
        )

    handler = SERVICE_HANDLERS.get(service)
    if not handler:
        raise HTTPException(
            status_code=500,
            detail={"error": "service detected but no handler found", "service": service}
        )

    try:
        metadata = await handler(url_str)

        # cache the full metadata (with urls/headers)
        cache_metadata(url_str, metadata)

        # return sanitized version (without urls/headers)
        return sanitize_metadata_for_response(metadata)

    except SERVICE_ERRORS.get(service, Exception) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "service": service}
        )

@app.post("/sodalite/process", response_model=ProcessResponse)
async def process_download(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    url_str = str(request.url)
    cache_key = get_cache_key(url_str)

    # try to get metadata from cache first
    cached_metadata = get_cached_metadata(url_str)
    if cached_metadata:
        print(f"using cached metadata for download: {url_str}")
        metadata = cached_metadata
    else:
        # fetch fresh metadata
        service = detect_service(url_str)
        if service == "unknown":
            raise HTTPException(status_code=400, detail="unsupported service")

        handler = SERVICE_HANDLERS.get(service)
        if not handler:
            raise HTTPException(status_code=500, detail="handler not found")

        try:
            metadata = await handler(url_str)
            # cache the metadata
            metadata_dict = metadata.model_dump() if hasattr(metadata, 'model_dump') else metadata.__dict__
            metadata_cache[cache_key] = {
                "metadata": metadata_dict,
                "timestamp": time.time()
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    task_id = generate_task_id(url_str)
    tasks[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "url": url_str,
        "service": metadata.service,
        "video_quality": request.video_quality,
        "audio_quality": request.audio_quality,
    }
    task_phases[task_id] = "initializing"

    background_tasks.add_task(
        process_download_task,
        task_id,
        metadata,
        request
    )
    return ProcessResponse(task_id=task_id, status="processing")

@app.get(
    "/sodalite/task/{task_id}",
    response_model=ProcessResponse
)
async def get_task_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    return ProcessResponse(
        task_id=task_id,
        status=task["status"],
        download_url=task.get("download_url"),
        error=task.get("error"),
        file_size_mb=task.get("file_size_mb"),
        video_quality=task.get("video_quality"),
        audio_quality=task.get("audio_quality")
    )

@app.get("/sodalite/task/{task_id}/phase")
async def get_task_phase(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    # get phase from task_phases dict or task dict
    phase = task_phases.get(task_id, task.get("phase", "unknown"))

    return {
        "task_id": task_id,
        "phase": phase,
        "status": task["status"]
    }

@app.get("/sodalite/download/{task_id}/file")
async def download_file(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={"error": "task not found"}
        )

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail={"error": f"task is {task['status']}, not completed"}
        )

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={"error": "file not found"}
        )

    # determine media type
    _, ext = os.path.splitext(file_path)
    media_type_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".opus": "audio/opus",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav"
    }
    media_type = media_type_map.get(ext.lower(), "application/octet-stream")

    filename = os.path.basename(file_path)

    return FileResponse(
        file_path,
        filename=filename,
        media_type=media_type
    )

@app.get(
    "/sodalite/services",
    response_model=ServicesResponse
)
async def list_services():
    return ServicesResponse(services=SERVICE_INFO)

@app.get("/sodalite/health")
async def health_check():
    global heartbeat_count
    heartbeat_count += 1
    await broadcast_stats()
    return {
        "status": "ok",
        "heartbeats": heartbeat_count,
        "connected_clients": len(active_websockets),
        "total_conversions": stats.total_conversions,
        "total_bandwidth_mb": round(stats.total_bandwidth_bytes / (1024 * 1024), 2)
    }

@app.websocket("/sodalite/ws/stats")
async def websocket_stats(websocket: WebSocket):
    global stats_broadcast_task
    await websocket.accept()
    active_websockets.append(websocket)

    # start periodic broadcasting if this is the first connection
    if len(active_websockets) == 1 and (stats_broadcast_task is None or stats_broadcast_task.done()):
        stats_broadcast_task = asyncio.create_task(periodic_stats_broadcast())

    try:
        # send initial stats
        await websocket.send_text(json.dumps({
            "type": "stats",
            "heartbeats": heartbeat_count,
            "connected_clients": len(active_websockets),
            "total_conversions": stats.total_conversions,
            "total_bandwidth_mb": round(stats.total_bandwidth_bytes / (1024 * 1024), 2)
        }))

        # keep connection alive and handle incoming messages
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # send ping to keep connection alive
                await websocket.send_text(json.dumps({"type": "ping"}))
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"websocket error: {e}")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

        # stop periodic broadcasting if no connections left
        if not active_websockets and stats_broadcast_task and not stats_broadcast_task.done():
            stats_broadcast_task.cancel()

@app.get("/sodalite/git-info")
async def git_info():
    try:
        repo = git.Repo(search_parent_directories=True)
        branch = repo.active_branch.name
        commit = repo.head.commit
        commit_sha = commit.hexsha
        commit_date = commit.committed_datetime.isoformat()
        commit_message = commit.message.strip()

        return {
            "branch": branch,
            "commit_sha": commit_sha,
            "commit_date": commit_date,
            "commit_message": commit_message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get git info: {str(e)}")

@app.delete("/sodalite/task/{task_id}")
async def cleanup_task(task_id: str):
    """manually clean up a task and its files"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    # remove file if it exists
    file_path = task.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"failed to remove file {file_path}: {e}")

    # remove from task tracking
    if task_id in tasks:
        del tasks[task_id]

    if task_id in task_phases:
        del task_phases[task_id]

    return {"message": "task cleaned up successfully"}

@app.get("/sodalite/cache/stats")
async def get_cache_stats():
    """get metadata cache statistics"""
    total_entries = len(metadata_cache)
    valid_entries = sum(1 for entry in metadata_cache.values() if is_cache_valid(entry))

    return {
        "total_entries": total_entries,
        "valid_entries": valid_entries,
        "invalid_entries": total_entries - valid_entries
    }

@app.delete("/sodalite/cache")
async def clear_cache():
    """clear metadata cache"""
    global metadata_cache
    cache_size = len(metadata_cache)
    metadata_cache.clear()
    return {"message": f"cleared {cache_size} cache entries"}
