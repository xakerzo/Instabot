import re

def extract_instagram_url(text: str) -> str:
    """
    Matn ichidan Instagram linkini ajratib oladi.
    """
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:p|reels|reel|tv)/[A-Za-z0-9_-]+)'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def is_instagram_url(url: str) -> bool:
    """
    Link Instagram'ga tegishli ekanligini tekshiradi.
    """
    return bool(extract_instagram_url(url))
