import os
from dotenv import load_dotenv

load_dotenv()

def get_db_url() -> str:
    # Railway, Heroku va boshqa cloud platformalar 'DATABASE_URL' yoki 'DB_URL' beradi
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "sqlite+aiosqlite:///./data/bot.db"
    
    # SQLAlchemy 2.x async engine uchun 'postgres://' yoki 'postgresql://' -> 'postgresql+asyncpg://'
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    return url

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
    
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_HOST = os.getenv("REDISHOST", os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT = int(os.getenv("REDISPORT", os.getenv("REDIS_PORT", 6379)))
    REDIS_PASSWORD = os.getenv("REDISPASSWORD", os.getenv("REDIS_PASSWORD")) or None
    
    DB_URL = get_db_url()
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    
    INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES")
    
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 49))
    USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
    PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "./proxies.txt")
    CACHE_TTL = 3600 * 24 * 7 

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
