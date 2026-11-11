import re
from typing import Optional

INSTAGRAM_REGEX = re.compile(
    r'(https?://(?:www\.)?(?:instagram\.com|instagr\.am)/(?:p|reel|reels|tv|stories|share/(?:p|reel)?)/[A-Za-z0-9_.-]+)',
    re.IGNORECASE
)

def extract_instagram_url(text: str) -> Optional[str]:
    """
    Matn ichidan Instagram linkini ajratib oladi va tozalaydi.
    """
    if not text:
        return None
    match = INSTAGRAM_REGEX.search(text.strip())
    if match:
        url = match.group(1)
        # /share/reel/CODE yoki /share/CODE larni standart formatga keltirish
        if "/share/reel/" in url:
            url = url.replace("/share/reel/", "/reel/")
        elif "/share/p/" in url:
            url = url.replace("/share/p/", "/p/")
        elif "/reels/" in url:
            url = url.replace("/reels/", "/reel/")
        return url
    return None

def is_instagram_url(url: str) -> bool:
    """
    Link Instagram'ga tegishli ekanligini tekshiradi.
    """
    return bool(extract_instagram_url(url))
