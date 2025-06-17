"""
metadata models for sodalite services
"""

from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Video(BaseModel):
    """a video download option"""
    url: HttpUrl
    quality: str  # e.g. "1080p"
    width: Optional[int] = None
    height: Optional[int] = None

class Audio(BaseModel):
    """an audio download option"""
    url: HttpUrl
    quality: str # e.g. "128kbps"

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
