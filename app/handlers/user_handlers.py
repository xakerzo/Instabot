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
    
    if cached:
        if cached.media_type == 'video':
            await message.reply_video(cached.file_id, caption="✅ Keshdan yuborildi")
        else:
            await message.reply_audio(cached.file_id)
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎬 Video", callback_data=f"dl:video:{url_hash}"),
        types.InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl:audio:{url_hash}")
    )
    
    redis = await create_pool(get_redis_settings())
    await redis.setex(f"url:{url_hash}", 3600, url)
    await message.reply("Formatni tanlang:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("dl:"))
async def process_download(callback: types.CallbackQuery):
    _, mode, url_hash = callback.data.split(":")
    redis = await create_pool(get_redis_settings())
    url = await redis.get(f"url:{url_hash}")
    
    if not url:
        await callback.answer("❌ Eskirgan havola.", show_alert=True)
        return

    msg = await callback.message.edit_text("📥 Navbatga qo'shildi...")
    await redis.enqueue_job('download_task', callback.from_user.id, url.decode(), mode, msg.message_id)
    await callback.answer()
