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


    return "unknown"
