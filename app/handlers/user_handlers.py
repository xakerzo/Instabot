from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from arq import create_pool
from arq.connections import RedisSettings

from config import Config
from database import add_user, get_cached_media
from app.utils.validators import extract_urls
from app.services.downloader import DownloaderService

router = Router()
downloader = DownloaderService()

def get_redis_settings():
    if Config.REDIS_URL:
        return RedisSettings.from_dsn(Config.REDIS_URL)
    return RedisSettings(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        password=Config.REDIS_PASSWORD
    )

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer("👋 Xush kelibsiz! Botga video linkini yuboring.")

@router.message(F.text)
async def handle_url(message: types.Message):
    urls = extract_urls(message.text)
    if not urls: return
    
    url = urls[0]
    url_hash = downloader.get_url_hash(url)
    cached = await get_cached_media(url_hash)
    
    # Keshda bo'lsa darhol yuboramiz
    if cached and cached.media_type == 'video':
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🎵 MP3 formatda olish", callback_data=f"dl:audio:{url_hash}"))
        await message.reply_video(cached.file_id, caption="✅ @YourBot orqali yuklandi", reply_markup=builder.as_markup())
        return

    # Keshda bo'lmasa navbatga qo'shamiz
    msg = await message.reply("⏳ Yuklash navbatiga qo'shildi...")
    
    redis = await create_pool(get_redis_settings())
    # URLni redisda saqlash
    await redis.setex(f"url:{url_hash}", 3600, url)
    # Workerni ishga tushirish (default video rejimida)
    await redis.enqueue_job('download_task', message.from_user.id, url, 'video', msg.message_id)
