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

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(
        "👋 Xush kelibsiz!\n\nMen Instagram, TikTok, YouTube va Pinterest'dan media yuklab beraman.\n"
        "Menga shunchaki link yuboring."
    )

@router.message(F.text)
async def handle_url(message: types.Message):
    urls = extract_urls(message.text)
    if not urls:
        return
    
    url = urls[0]
    user_id = message.from_user.id
    url_hash = downloader.get_url_hash(url)

    # 1. Keshni tekshirish
    cached = await get_cached_media(url_hash)
    if cached:
        if cached.media_type == 'video':
            await message.reply_video(cached.file_id, caption="✅ Keshdan yuborildi")
        elif cached.media_type == 'audio':
            await message.reply_audio(cached.file_id)
        return

    # 2. Tanlov tugmalari
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎬 Video", callback_data=f"dl:video:{url_hash}"),
        types.InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl:audio:{url_hash}")
    )
    
    # URL ni vaqtincha redis'da saqlab turish (yoki callback_data'da yuborish, lekin u 64 bayt limit)
    # Biz hozircha soddalik uchun prompt'da URL ni saqlamaymiz, 
    # lekin professional botda bu URL redis'da url_hash orqali saqlanishi kerak.
    # Keling, redis pool yaratamiz:
    redis = await create_pool(RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT))
    await redis.setex(f"url:{url_hash}", 3600, url)

    await message.reply("Qaysi formatda yuklamoqchisiz?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("dl:"))
async def process_download(callback: types.CallbackQuery):
    _, mode, url_hash = callback.data.split(":")
    
    redis = await create_pool(RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT))
    url = await redis.get(f"url:{url_hash}")
    
    if not url:
        await callback.answer("❌ Link muddati eskirgan, qayta yuboring.", show_alert=True)
        return

    # Progress xabari (Worker buni o'zgartiradi)
    msg = await callback.message.edit_text("📥 Navbatga qo'shildi...")
    
    # Arq orqali worker'ga topshiriq berish
    await redis.enqueue_job('download_task', callback.from_user.id, url.decode(), mode, msg.message_id)
    await callback.answer("Vazifa navbatga qo'shildi!")
