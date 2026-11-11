import re
from typing import Optional, Tuple

INSTAGRAM_REGEX = re.compile(
    r'https?://(?:www\.)?(?:instagram\.com|instagr\.am)/(?:p|reel|reels|tv|stories|share/(?:p|reel)?)/[A-Za-z0-9_.-]+',
    re.IGNORECASE
)

TIKTOK_REGEX = re.compile(
    r'https?://(?:(?:www|m|vt|vm)\.)?tiktok\.com/(?:@[\w.-]+/(?:video|photo)/\d+|t/\w+|[\w.-]+)',
    re.IGNORECASE
)

PINTEREST_REGEX = re.compile(
    r'https?://(?:[a-z]{2}\.)?(?:pinterest\.(?:com|[a-z]{2})|pin\.it)/(?:pin/\d+|[\w.-]+)',
    re.IGNORECASE
)

YOUTUBE_REGEX = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/shorts/|youtu\.be/)[A-Za-z0-9_-]+',
    re.IGNORECASE
)

def extract_media_url(text: str) -> Optional[Tuple[str, str]]:
    """
    Matn ichidan Instagram, TikTok, Pinterest yoki YouTube Shorts havolasini ajratib oladi.
    Qaytaradi: (url, platform) yoki None
    """
    if not text:
        return None
    text = text.strip()

    # 1. Instagram
    match = INSTAGRAM_REGEX.search(text)
    if match:
        url = match.group(0)
        if "/share/reel/" in url:
            url = url.replace("/share/reel/", "/reel/")
        elif "/share/p/" in url:
            url = url.replace("/share/p/", "/p/")
        elif "/reels/" in url:
            url = url.replace("/reels/", "/reel/")
        return url, "instagram"

    # 2. TikTok
    match = TIKTOK_REGEX.search(text)
    if match:
        return match.group(0), "tiktok"

    # 3. Pinterest
    match = PINTEREST_REGEX.search(text)
    if match:
        return match.group(0), "pinterest"

    # 4. YouTube Shorts
    match = YOUTUBE_REGEX.search(text)
    if match:
        return match.group(0), "youtube"

    return None

def extract_instagram_url(text: str) -> Optional[str]:
    """Orqaga moslik (Backwards compatibility) uchun"""
    res = extract_media_url(text)
    if res and res[1] == "instagram":
        return res[0]
    return None

def is_supported_url(text: str) -> bool:
    """Havola qo'llab-quvvatlanadigan platformaga tegishli ekanligini tekshiradi"""
    return extract_media_url(text) is not None
