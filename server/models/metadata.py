"""
metadata models for sodalite services
"""

from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional

class Video(BaseModel):
    """a video download option"""
    url: Optional[HttpUrl] = None
    headers: Optional[Dict[str, str]] = None  # optional headers for the request
    quality: str  # e.g. "1080p"
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None  # video codec info

class Audio(BaseModel):
    """an audio download option"""
    url: Optional[HttpUrl] = None
    headers: Optional[Dict[str, str]] = None  # optional headers for the request
    quality: str # e.g. "128kbps"
    codec: Optional[str] = None  # audio codec info

class SodaliteMetadata(BaseModel):
    """
    the metadata for a sodalite link preview
    """
    service: str
    title: str
    author: str # just the name
    thumbnail_url: Optional[HttpUrl] = None
    videos: List[Video] = []
    audios: List[Audio] = []

class SanitizedVideo(BaseModel):
    """a video download option without sensitive info"""
    quality: str
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None

class SanitizedAudio(BaseModel):
    """an audio download option without sensitive info"""
    quality: str
    codec: Optional[str] = None

class SanitizedSodaliteMetadata(BaseModel):
    """sanitized metadata for API response"""
    service: str
    title: str
    author: str
    thumbnail_url: Optional[HttpUrl] = None
    videos: List[SanitizedVideo] = []
    audios: List[SanitizedAudio] = []
