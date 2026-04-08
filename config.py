import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
    
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_HOST = os.getenv("REDISHOST", os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT = int(os.getenv("REDISPORT", os.getenv("REDIS_PORT", 6379)))
    REDIS_PASSWORD = os.getenv("REDISPASSWORD", os.getenv("REDIS_PASSWORD"))
    
    DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/bot.db")
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    
    INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES")
    
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
    PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "./proxies.txt")
    CACHE_TTL = 3600 * 24 * 7 

# Kukilarni mustahkamroq yozish
if Config.INSTAGRAM_COOKIES:
    content = Config.INSTAGRAM_COOKIES.strip()
    # Netscape sarlavhasi yo'q bo'lsa, qo'shib qo'yamiz
    if not content.startswith("# Netscape"):
        content = "# Netscape HTTP Cookie File\n" + content
        
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Instagram Cookies fayli yuklandi ({len(content)} bayt)")

os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
os.makedirs("./data", exist_ok=True)
