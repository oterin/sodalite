"""
YouTube service module for Sodalite.
Provides functionality to extract metadata and stream URLs from YouTube videos.
"""

from .handler import fetch_dl, YouTubeError

__all__ = ['fetch_dl']
