from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from arq import create_pool
from arq.connections import RedisSettings

from config import Config
from database import get_from_cache, add_user, increment_stats
from app.utils.validators import extract_instagram_url
from app.services.downloader import DownloaderService

router = Router()

async def get_redis():
    if Config.REDIS_URL:
        return await create_pool(RedisSettings.from_dsn(Config.REDIS_URL))
    return await create_pool(RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT, password=Config.REDIS_PASSWORD))

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)
    bot_info = await message.bot.get_me()
    await message.answer(
        "👋 Assalomu alaykum!\n\nMen Instagramdan video va rasmlarni yuklab beruvchi botman.\nLinkni yuboring:",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_info.username}?startgroup=true")
        ).as_markup()
    )

@router.message(F.text)
async def handle_message(message: types.Message):
    url = extract_instagram_url(message.text)
    if not url:
        if message.chat.type in ['group', 'supergroup']:
            return
        return await message.answer("❌ Bu Instagram linki emas!")

    await add_user(message.from_user.id, message.from_user.username)
    await increment_stats()

    url_hash = DownloaderService.get_url_hash(url)
    
    cached = await get_from_cache(url_hash)
    if cached and cached.file_type == 'video':
        bot_user = await message.bot.get_me()
        bot_username = bot_user.username
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data="cached"))
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))

        return await message.reply_video(
            cached.file_id, 
            caption=f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩",
            reply_markup=builder.as_markup()
        )

    wait_msg = await message.answer("⏳ Navbatga qo'shildi...")
    redis = await get_redis()
    await redis.enqueue_job('download_task', message.chat.id, url, 'video', wait_msg.message_id)

@router.callback_query(F.data == "cached")
async def handle_cached_callback(callback: types.CallbackQuery):
    await callback.answer("✅ Ushbu video bot keshida saqlangan!", show_alert=False)
