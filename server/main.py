"""
sodalite api server - the main entry point
"""

import os
import tempfile
import hashlib
import json
import redis
from datetime import datetime
from pydantic.json import pydantic_encoder

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal

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
# in a real prod app, you'd want to be more restrictive
# but for this project, we'll allow all origins
origins = [
    "http://localhost:3000",
    "https://sodalite-frontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # gonna need to change this in prod
                         # but for now we chilling
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Connect to Redis
# Render provides the REDIS_URL environment variable
redis_url = os.environ.get("REDIS_URL")
if not redis_url:
    print("WARNING: REDIS_URL environment variable not set. Using in-memory storage.")
    # Fallback to a mock Redis for local dev if you don't have Redis installed
    # For production, this should throw an error.
    from unittest.mock import Mock
    r = Mock()
    r.hgetall = Mock(return_value=None)
    r.hset = Mock()
    r.delete = Mock()

else:
    r = redis.from_url(redis_url, decode_responses=True)


# request/response models
class DownloadRequest(BaseModel):
    url: HttpUrl

class ProcessRequest(BaseModel):
    url: HttpUrl
    video_quality: Optional[str] = None
    audio_quality: Optional[str] = None
    format: str = "mp4"
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
        r.hset(task_id, "status", "processing")

        # download and merge the streams
        output_path = await download_and_merge(
            metadata=metadata,
            video_quality=request.video_quality,
            audio_quality=request.audio_quality,
            output_format=request.format,
            output_dir=DOWNLOAD_DIR,
            download_mode=request.download_mode
        )

        # update task status in Redis
        r.hset(task_id, mapping={
            "status": "completed",
            "download_url": f"/api/download/{task_id}/file",
            "file_path": output_path
        })


    except Exception as e:
        r.hset(task_id, mapping={
            "status": "failed",
            "error": str(e)
        })

        # log for debugging rq
        import traceback
        traceback.print_exc()

@app.post(
    "/api/download",
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
    "/api/process",
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
async def process_download(
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

        # Serialize complex objects to JSON strings for Redis
        task_data = {
            "status": "processing",
            "metadata": json.dumps(metadata, default=pydantic_encoder),
            "request": json.dumps(request, default=pydantic_encoder),
            "created_at": datetime.now().isoformat(),
        }
        r.hset(task_id, mapping=task_data)
        r.expire(task_id, 3600) # Expire task data after 1 hour

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
    "/api/task/{task_id}",
    response_model=ProcessResponse
)
async def get_task_status(task_id: str):
    """
    get the status of a download task
    """
    task = r.hgetall(task_id)
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

@app.get("/api/download/{task_id}/file")
async def download_file(task_id: str):
    """
    download the processed file for a task
    """
    task = r.hgetall(task_id)
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

    # Deserialize metadata and request from JSON
    metadata = SodaliteMetadata(**json.loads(task["metadata"]))
    request_data = ProcessRequest(**json.loads(task["request"]))

    filename = f"{metadata.title[:50]}_{metadata.author[:30]}.{request_data.format}".replace(" ", "_").replace("/", "_")
    filename = "".join(c for c in filename if c.isalnum() or c in "._-") # sanitizing the filename (we don't want any funny business)

    # return the file response
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=(
            "video/mp4" if request_data.format == "mp4" else
            f"video/{request_data.format.replace(" (muxed)", "")}"
        )
    )

@app.get(
    "/api/services",
    response_model=ServicesResponse
)
async def list_services():
    """
    list all supported services
    """
    return ServicesResponse(services=SERVICE_INFO)

@app.get("/api/health")
async def health_check():
    """
    health check endpoint
    """
    # check if ffmpeg is available
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        ffmpeg_available = True
    except:
        ffmpeg_available = False

    # Check redis connection
    redis_available = False
    if r:
        try:
            r.ping()
            redis_available = True
        except:
            redis_available = False


    return {
        "status": "ok",
        "ffmpeg_available": ffmpeg_available,
        "redis_available": redis_available,
        "temp_dir": DOWNLOAD_DIR
    }

@app.delete("/api/task/{task_id}")
async def cleanup_task(task_id: str):
    """
    cleanup a task and its associated files
    """
    task = r.hgetall(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "task not found"})

    # delete file if exists
    file_path = task.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    # remove task from Redis
    r.delete(task_id)

    return {"status": "cleaned"}
