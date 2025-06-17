"""
sodalite metadata format

this holds our standardized metadata model that all services return
"""

from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class VideoQuality(BaseModel):
    """
    a single video download option
    """
    url: HttpUrl
    quality_label: str # e.g., "1080p", "720p"
    width: Optional[int] = None
    height: Optional[int] = None
    bitrate: Optional[int] = None
    mime_type: Optional[str] = None # e.g., "video/mp4"

class AudioQuality(BaseModel):
    """
    a single audio download option
    """
    url: HttpUrl
    quality_label: str # e.g., "128kbps"
    bitrate: Optional[int] = None
    mime_type: Optional[str] = None # e.g., "audio/mp4"

class Author(BaseModel):
    """
    creator info
    """
    username: str
    display_name: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    avatar_url: Optional[HttpUrl] = None

class SodaliteMetadata(BaseModel):
    """
    unified metadata format for all services
    """
    service: str
    source_url: HttpUrl
    title: str
    description: Optional[str] = None
    author: Author
    thumbnail_url: Optional[HttpUrl] = None
    videos: List[VideoQuality] = []
    audios: List[AudioQuality] = []
