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
from typing import Optional, Literal, List
import git
import asyncio
import json
import aiofiles

from server.helper.detector import detect_service
from server.helper.errors import (
    InstagramReelsError,
    YouTubeError,
    TikTokError
)
from server.models.metadata import SodaliteMetadata
from server.services import (
    instagram_reels,
    youtube,
    tiktok
)
from server.helper.downloader import download_and_merge

# sodalite app instance
app = FastAPI(
    title="sodalite",
    description="a simple downloader for the web - no ads, no tracking, just downloads",
    version="0.1.0"
)

# cors middleware (because we like, need that lol)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://backend.otter.llc", "https://sodalite.otter.llc"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# request model
# request/response models
class DownloadRequest(BaseModel):
    url: HttpUrl

class ProcessRequest(BaseModel):
    url: HttpUrl
    video_quality: Optional[str] = None  # if None, use best
    audio_quality: Optional[str] = None  # if None, use best
    format: Literal["mp4", "webm", "mkv", "mp3", "m4a"] = "mp4"
    download_mode: Literal["default", "video_only", "audio_only"] = "default"

class ProcessResponse(BaseModel):
    task_id: str
    status: Literal["processing", "completed", "failed"]
    download_url: Optional[str] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    service: Optional[str] = None

class ServiceInfo(BaseModel):
    name: str
    example_urls: list[str]

class ServicesResponse(BaseModel):
    services: dict[str, ServiceInfo]

# tempdir for dls
TEMP_DIR = tempfile.gettempdir()
DOWNLOAD_DIR = os.path.join(TEMP_DIR, "sodalite_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory store for tasks (replace Vercel KV)
# In a real-world scenario, this would ideally be a proper database or a persistent key-value store
# as this will not persist across server restarts.
tasks = {}

# Global heartbeat counter
heartbeat_count = 0

# WebSocket connections for live heartbeat updates
active_websockets: List[WebSocket] = []

# Statistics tracking
STATS_FILE = os.path.join(DOWNLOAD_DIR, "sodalite_stats.json")

class Statistics:
    def __init__(self):
        self.total_conversions = 0
        self.total_bandwidth_bytes = 0
        self.load_from_file()

    def load_from_file(self):
        """Load stats from file if it exists"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    data = json.load(f)
                    self.total_conversions = data.get('total_conversions', 0)
                    self.total_bandwidth_bytes = data.get('total_bandwidth_bytes', 0)
        except Exception as e:
            print(f"Failed to load stats: {e}")

    async def save_to_file(self):
        """Save stats to file"""
        try:
            data = {
                'total_conversions': self.total_conversions,
                'total_bandwidth_bytes': self.total_bandwidth_bytes,
                'last_updated': datetime.now().isoformat()
            }
            async with aiofiles.open(STATS_FILE, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save stats: {e}")

    async def increment_conversion(self):
        """Increment conversion count and save"""
        self.total_conversions += 1
        await self.save_to_file()

    async def add_bandwidth(self, bytes_count: int):
        """Add to bandwidth usage and save"""
        self.total_bandwidth_bytes += bytes_count
        await self.save_to_file()

# Global statistics instance
stats = Statistics()

# service mapping (should be extensible 💐)
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
        name="YouTube Shorts",
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
    """generates a unique task id for the given url"""
    # there's NO 🙅🏻‍♂️ way two requests will have the same url and timestamp, right? 😅
    timestamp = datetime.now().isoformat()
    return hashlib.md5(f"{url}{timestamp}".encode()).hexdigest()

async def process_download_task(
    task_id: str,
    metadata: SodaliteMetadata,
    request: ProcessRequest
):
    """
    background task to download and merge the video and audio streams
    because most services LOOOOOOOVE to separate them for some odd fuCKING REASOn
    """
    try:
        # Update status in local tasks dictionary
        tasks[task_id]["status"] = "processing"

        # download and merge the streams
        output_path = await download_and_merge(
            metadata=metadata,
            video_quality=request.video_quality,
            audio_quality=request.audio_quality,
            output_format=request.format,
            output_dir=DOWNLOAD_DIR,
            download_mode=request.download_mode
        )

        # update task status
        tasks[task_id].update({
            "status": "completed",
            "download_url": f"/sodalite/download/{task_id}/file",
            "file_path": output_path
        })

        # track conversion statistics
        await stats.increment_conversion()
        await broadcast_stats()

    except Exception as e:
        tasks[task_id].update({"status": "failed", "error": str(e)})

        # log for debugging rq
        import traceback
        traceback.print_exc()

@app.post(
    "/sodalite/download",
    response_model=SodaliteMetadata,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid URL or service not supported"
        }
    }
)
async def get_download_info(request: DownloadRequest):
    """
    extract download information from a supported service url
    """
    url_str = str(request.url)

    # detect service
    service = detect_service(url_str)

    if service == "unknown":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported service",
                "service": None
            }
        )

    # get the handler
    handler = SERVICE_HANDLERS.get(service)
    if not handler:
        raise HTTPException(
            status_code=500,
            detail={"error": "service detected but no handler found", "service": service}
        )

    try:
        # fetch the metadata
        metadata = await handler(url_str)
        return metadata

    except SERVICE_ERRORS.get(service, Exception) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "service": service}
        )

@app.post(
    "/sodalite/process",
    response_model=ProcessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid URL or service not supported"
        },
        404: {
            "model": ErrorResponse,
            "description": "Not Found - Task ID not found"
        }
    }
)
async def proces_download(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    process a download (download video/audio and merge with metadata)
    """
    url_str = str(request.url)

    # first we grab the metadata
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

        # create task
        task_id = generate_task_id(url_str)

        # Serialize complex objects to JSON strings for local storage
        task_data = {
            "status": "processing",
            "metadata": metadata.model_dump_json(),
            "request": request.model_dump_json(),
            "created_at": datetime.now().isoformat(),
        }

        # Use local dictionary to store the task data
        tasks[task_id] = task_data
        # Note: In-memory tasks will not persist across server restarts.
        # No explicit expiration for in-memory tasks as `timedelta` is for KV.

        # start background task to download the task
        background_tasks.add_task(
            process_download_task,
            task_id,
            metadata,
            request
        )

        return ProcessResponse(
            task_id=task_id,
            status="processing"
        )

    except SERVICE_ERRORS.get(service, Exception) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "service": service}
        )

@app.get(
    "/sodalite/task/{task_id}",
    response_model=ProcessResponse
)
async def get_task_status(task_id: str):
    """
    get the status of a download task
    """
    # Use local dictionary to get the task
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={"error": "task not found"}
        )

    return ProcessResponse(
        task_id=task_id,
        status=task["status"],
        download_url=task.get("download_url"),
        error=task.get("error")
    )

@app.get("/sodalite/download/{task_id}/file")
async def download_file(task_id: str):
    """
    download the processed file for a task
    """
    # Use local dictionary to get the task
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={"error": "task not found"}
        )

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail={"error": "task is not completed yet"}
        )

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={"error": "file not found"}
        )

    # get original filename for metadata
    metadata_json = task.get("metadata")
    request_json = task.get("request")

    if not metadata_json or not request_json:
        raise HTTPException(
            status_code=500,
            detail={"error": "Task data incomplete in local store, cannot determine file properties."}
        )

    metadata = SodaliteMetadata.parse_raw(metadata_json)
    request_obj = ProcessRequest.parse_raw(request_json)

    filename = f"{metadata.title[:50]}_{metadata.author[:30]}.{request_obj.format}".replace(" ", "_").replace("/", "_")
    filename = "".join(c for c in filename if c.isalnum() or c in "._-") # sanitizing the filename (we don't want any funny business)

    # track bandwidth usage
    file_size = os.path.getsize(file_path)
    await stats.add_bandwidth(file_size)
    await broadcast_stats()

    # return the file response
    media_type_map = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4"
    }

    file_format = request_obj.format
    media_type = media_type_map.get(file_format, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )

@app.get(
    "/sodalite/services",
    response_model=ServicesResponse
)
async def list_services():
    """
    list all supported services
    """
    return ServicesResponse(services=SERVICE_INFO)

async def broadcast_stats():
    """broadcast stats to all connected websockets"""
    if active_websockets:
        message = json.dumps({
            "type": "stats",
            "heartbeats": heartbeat_count,
            "connected_clients": len(active_websockets),
            "total_conversions": stats.total_conversions,
            "total_bandwidth_mb": round(stats.total_bandwidth_bytes / (1024 * 1024), 2)
        })
        disconnected = []
        for websocket in active_websockets:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)

        # Remove disconnected websockets
        for ws in disconnected:
            if ws in active_websockets:
                active_websockets.remove(ws)

@app.get("/sodalite/health")
async def health_check():
    """
    health check endpoint
    """
    global heartbeat_count
    heartbeat_count += 1

    # Broadcast to all connected websockets
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
    """websocket endpoint for live stats updates"""
    await websocket.accept()
    active_websockets.append(websocket)

    try:
        # Send current stats immediately
        await websocket.send_text(json.dumps({
            "type": "stats",
            "heartbeats": heartbeat_count,
            "connected_clients": len(active_websockets),
            "total_conversions": stats.total_conversions,
            "total_bandwidth_mb": round(stats.total_bandwidth_bytes / (1024 * 1024), 2)
        }))

        # Broadcast updated client count to all
        await broadcast_stats()

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        # Broadcast updated client count
        await broadcast_stats()

@app.get("/sodalite/git-info")
async def git_info():
    """
    get git information for the repo
    """
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
    except git.InvalidGitRepositoryError:
        raise HTTPException(status_code=500, detail="not a git repository")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"an error occurred: {str(e)}")


@app.delete("/sodalite/task/{task_id}")
async def cleanup_task(task_id: str):
    """
    cleanup a task and its associated files
    """
    # Use local dictionary to get the task
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "task not found"})

    # delete file if exists
    file_path = task.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    # remove task from local dictionary
    if task_id in tasks:
        del tasks[task_id]

    return {"status": "cleaned"}
