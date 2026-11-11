import os
import urllib.parse
import logging
from typing import Optional
from dotenv import load_dotenv
import redis
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

def resolve_redis_settings(settings: RedisSettings) -> RedisSettings:
    """
    Redis serveriga turli usullar bilan ulanishni sinab ko'radi va avtomatik ishlaydiganini topadi:
    1. Sozlangan (username, password) bilan
    2. Faqat parol bilan (usernamesiz)
    3. Parolsiz (chunki ko'pincha Coolify Redis-da parol bo'lmaydi)
    """
    # 1-sinov: Sozlangan parametrlar bilan
    try:
        r = redis.Redis(
            host=settings.host,
            port=settings.port,
            username=settings.username,
            password=settings.password,
            db=settings.database,
            ssl=settings.ssl,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        r.ping()
        logging.info(f"✅ Redis-ga muvaffaqiyatli ulandi (user='{settings.username}')")
        return settings
    except redis.AuthenticationError:
        logging.warning("⚠️ Redis autentifikatsiyani rad etdi. Muqobil variantlar sinab ko'rilmoqda...")
    except Exception as e:
        return settings

    # 2-sinov: Faqat parol bilan (usernamesiz)
    if settings.password:
        try:
            r = redis.Redis(
                host=settings.host,
                port=settings.port,
                username=None,
                password=settings.password,
                db=settings.database,
                ssl=settings.ssl,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            r.ping()
            logging.info("✅ Redis-ga faqat parol bilan (usernamesiz) muvaffaqiyatli ulandi!")
            settings.username = None
            return settings
        except redis.AuthenticationError:
            pass
        except Exception:
            return settings

    # 3-sinov: Parolsiz (agar Redis serverda parol o'rnatilmagan bo'lsa)
    try:
        r = redis.Redis(
            host=settings.host,
            port=settings.port,
            username=None,
            password=None,
            db=settings.database,
            ssl=settings.ssl,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        r.ping()
        logging.info("✅ Redis-ga PAROLSIZ muvaffaqiyatli ulandi! (Serverda parol yo'q ekan)")
        settings.username = None
        settings.password = None
        return settings
    except Exception as e:
        logging.error(f"❌ Redis parolsiz ham ulanmadi: {e}")

    return settings

def get_redis_settings() -> RedisSettings:
    """
    Redis ulanish parametrlarini xavfsiz va aniq qaytaradi.
    """
    if Config.REDIS_URL:
        url = Config.REDIS_URL.strip()
        parsed = urllib.parse.urlparse(url)
        username = urllib.parse.unquote(parsed.username) if parsed.username else None
        password = urllib.parse.unquote(parsed.password) if parsed.password else None
        
        if not username and password:
            username = "default"
            
        database = 0
        if parsed.path and parsed.path.lstrip("/").isdigit():
            database = int(parsed.path.lstrip("/"))
            
        settings = RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            username=username,
            password=password,
            database=database,
            ssl=parsed.scheme == "rediss"
        )
        return resolve_redis_settings(settings)

    username = Config.REDIS_USER
    if (not username or username == "") and Config.REDIS_PASSWORD:
        username = "default"
        
    settings = RedisSettings(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        username=username if Config.REDIS_PASSWORD else None,
        password=Config.REDIS_PASSWORD
    )
    return resolve_redis_settings(settings)

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
