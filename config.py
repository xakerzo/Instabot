import os
import urllib.parse
import logging
from typing import Optional, List
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

def mask_secret(p: Optional[str]) -> str:
    if not p:
        return "None (parolsiz)"
    if len(p) <= 4:
        return f"len={len(p)}: ****"
    return f"len={len(p)}: {p[:2]}***{p[-2:]}"

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
    Redis serveriga turli kombinatsiyalarni (username, password, nopass) sinab ko'radi
    va avtomatik tarzda 100% ishlaydigan parametrni aniqlab ulanadi.
    """
    hosts = [Config.REDIS_HOST]
    ports = [Config.REDIS_PORT]
    users = []
    passwords = []

    if Config.REDIS_USER:
        users.append(Config.REDIS_USER)
    users.extend(["default", None, "redis", "valkey", "root"])

    if Config.REDIS_PASSWORD:
        passwords.append(Config.REDIS_PASSWORD)

    if Config.REDIS_URL:
        try:
            parsed = urllib.parse.urlparse(Config.REDIS_URL)
            if parsed.hostname and parsed.hostname not in hosts:
                hosts.insert(0, parsed.hostname)
            if parsed.port and parsed.port not in ports:
                ports.insert(0, parsed.port)
            if parsed.username and parsed.username not in users:
                users.insert(0, urllib.parse.unquote(parsed.username))
            if parsed.password:
                unquoted_pwd = urllib.parse.unquote(parsed.password)
                if unquoted_pwd not in passwords:
                    passwords.append(unquoted_pwd)
        except Exception as e:
            logging.warning(f"REDIS_URL tahlil qilishda xatolik: {e}")

    # Takrorlanishlarni olib tashlash
    users = list(dict.fromkeys(users))
    passwords = list(dict.fromkeys(passwords))
    # Oxirgi chora sifatida parolsiz (None) ulanishni ham sinab ko'rish
    if None not in passwords:
        passwords.append(None)

    logging.info(f"Redis sinov variantlari: Hosts={hosts}, Users={users}, Parollar={len(passwords)} ta ({[mask_secret(p) for p in passwords]})")

    # Ishlaydigan kombinatsiyani qidirish
    for h in hosts:
        for p in ports:
            for pwd in passwords:
                for u in users:
                    try:
                        r = redis.Redis(
                            host=h,
                            port=p,
                            username=u,
                            password=pwd,
                            socket_timeout=1.0,
                            socket_connect_timeout=1.0
                        )
                        r.ping()
                        logging.info(f"🎯 KASHF ETILDI: Redis muvaffaqiyatli ulandi! Host: {h}:{p}, User: '{u}', Parol: {mask_secret(pwd)}")
                        return RedisSettings(
                            host=h,
                            port=p,
                            username=u,
                            password=pwd
                        )
                    except redis.AuthenticationError:
                        continue
                    except Exception as ex:
                        logging.debug(f"Ulanishda xato ({h}:{p}, user={u}): {ex}")
                        break

    logging.warning("⚠️ Sinovdagi hech bir parol/user kombinatsiyasi qabul qilinmadi. Standart parametrlar ishlatilmoqda.")
    return RedisSettings(
        host=hosts[0],
        port=ports[0],
        username=users[0] if passwords[0] else None,
        password=passwords[0]
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
