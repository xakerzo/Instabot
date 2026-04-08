import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
    
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    
    DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/bot.db")
    
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    
    # Telegram limitlari
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    
    # Proxy sozlamalari
    USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
    PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "./proxies.txt")

    # Kesh muddati (sekundda)
    CACHE_TTL = 3600 * 24 * 7  # 1 hafta

# Kataloglarni tekshirish
os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
os.makedirs("./data", exist_ok=True)
