import os
import urllib.parse
from typing import Optional
from dotenv import load_dotenv
from arq.connections import RedisSettings

load_dotenv()

def clean_str(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val or None

def get_db_url() -> str:
    url = clean_str(os.getenv("DATABASE_URL") or os.getenv("DB_URL")) or "sqlite+aiosqlite:///./data/bot.db"
    
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    return url

class Config:
    BOT_TOKEN = clean_str(os.getenv("BOT_TOKEN")) or ""
    ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
    
    REDIS_URL = clean_str(os.getenv("REDIS_URL"))
    REDIS_HOST = clean_str(os.getenv("REDISHOST") or os.getenv("REDIS_HOST")) or "localhost"
    REDIS_PORT = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT") or 6379)
    REDIS_USER = clean_str(os.getenv("REDISUSER") or os.getenv("REDIS_USER") or os.getenv("REDIS_USERNAME")) or "default"
    REDIS_PASSWORD = clean_str(os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD"))
    
    DB_URL = get_db_url()
    DOWNLOAD_PATH = clean_str(os.getenv("DOWNLOAD_PATH")) or "./downloads"
    
    INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES")
    
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB") or 49)
    USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
    PROXY_LIST_PATH = clean_str(os.getenv("PROXY_LIST_PATH")) or "./proxies.txt"
    CACHE_TTL = 3600 * 24 * 7 

def get_redis_settings() -> RedisSettings:
    """
    Redis ulanish parametrlarini xavfsiz va aniq qaytaradi.
    Redis 6/7 ACL (Coolify, Docker) da username 'default' bo'lishini ta'minlaydi.
    """
    if Config.REDIS_URL:
        url = Config.REDIS_URL.strip()
        parsed = urllib.parse.urlparse(url)
        username = urllib.parse.unquote(parsed.username) if parsed.username else None
        password = urllib.parse.unquote(parsed.password) if parsed.password else None
        
        # Agar parol bo'lsa va username bo'sh bo'lsa, 'default' foydalanuvchi qilib belgilaymiz
        if not username and password:
            username = "default"
            
        database = 0
        if parsed.path and parsed.path.lstrip("/").isdigit():
            database = int(parsed.path.lstrip("/"))
            
        return RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            username=username,
            password=password,
            database=database,
            ssl=parsed.scheme == "rediss"
        )

    # Alohida parametrlar berilganda
    username = Config.REDIS_USER
    if (not username or username == "") and Config.REDIS_PASSWORD:
        username = "default"
        
    return RedisSettings(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        username=username if Config.REDIS_PASSWORD else None,
        password=Config.REDIS_PASSWORD
    )

def setup_environment():
    """Tayyorgarlik amallari: papkalar yaratish va cookies faylini sozlash"""
    os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    
    if Config.INSTAGRAM_COOKIES:
        content = Config.INSTAGRAM_COOKIES.strip()
        if not content.startswith("# Netscape"):
            content = "# Netscape HTTP Cookie File\n" + content
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write(content)
