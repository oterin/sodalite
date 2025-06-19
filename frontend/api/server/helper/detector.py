"""
sodalite service detector
"""

def detect_service(url: str) -> str:
    """
    Detects the service based on the URL.

    Args:
        url (str): The URL to be checked.

    Returns:
        str: The name of the service if detected, otherwise 'unknown'.
    """

    # instagram reels division
    if (
        "instagram.com/reel" in url
        or "instagram.com/reels" in url
    ):
        return "instagram_reels"

    # youtube division
    if (
        "youtube.com/watch" in url
        or "youtu.be/" in url
        or "youtube.com/shorts" in url
    ):
        return "youtube"

    # tiktok division
    if (
        "tiktok.com/" in url
    ):
        return "tiktok"


    return "unknown"
