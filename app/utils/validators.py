import re

URL_PATTERN = re.compile(
    r'http(?:s)?://(?:www\.)?'
    r'(?:anchor\.fm|instagram\.com|tiktok\.com|youtube\.com|youtu\.be|pinterest\.com|pin\.it)/'
    r'\S+'
)

def is_valid_url(url: str) -> bool:
    return bool(URL_PATTERN.search(url))

def extract_urls(text: str) -> list:
    return URL_PATTERN.findall(text)
