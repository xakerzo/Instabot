import os
import asyncio
import traceback
from arq import create_pool
from arq.connections import RedisSettings
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config
from app.services.downloader import DownloaderService
from app.utils.video_processor import compress_video
import database

def get_redis_settings():
    if Config.REDIS_URL:
        return RedisSettings.from_dsn(Config.REDIS_URL)
    return RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT, password=Config.REDIS_PASSWORD)

bot = Bot(token=Config.BOT_TOKEN)
downloader = DownloaderService()

async def download_task(ctx, user_id: int, url: str, mode: str = 'video', message_id: int = None):
    url_hash = downloader.get_url_hash(url)
    try:
        await bot.edit_message_text("⏳ Yuklanmoqda...", chat_id=user_id, message_id=message_id)
        result = await downloader.download(url, mode)
        file_path = result['file_path']
        
        if mode == 'video' and result['file_size'] > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
            await bot.edit_message_text("⚙️ Optimizatsiya qilinmoqda...", chat_id=user_id, message_id=message_id)
            file_path = compress_video(file_path)

        await bot.edit_message_text("📤 Botga yuborilmoqda...", chat_id=user_id, message_id=message_id)
        
        sent_msg = None
        input_file = types.FSInputFile(file_path)
        
        if mode == 'audio':
            sent_msg = await bot.send_audio(
                chat_id=user_id,
                audio=input_file,
                title=result['title']
            )
        else:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="🎵 MP3 formatda olish", callback_data=f"dl:audio:{url_hash}"))
            
            sent_msg = await bot.send_video(
                chat_id=user_id,
                video=input_file,
                caption=f"✅ {result['title']}\n\n🤖 @YourBot",
                reply_markup=builder.as_markup()
            )

        if sent_msg:
            file_id = sent_msg.video.file_id if mode == 'video' else sent_msg.audio.file_id
            await database.add_to_cache(url_hash, file_id, mode, os.path.getsize(file_path))

        if os.path.exists(file_path): os.remove(file_path)
        await bot.delete_message(chat_id=user_id, message_id=message_id)

    except Exception as e:
        # Xatolikni to'liq ko'rsatish
        error_msg = traceback.format_exc()
        print(f"Detailed Worker Error: {error_msg}")
        await bot.send_message(user_id, f"❌ Xatolik yuz berdi:\n<code>{str(e)}</code>", parse_mode="HTML")

class WorkerSettings:
    functions = [download_task]
    redis_settings = get_redis_settings()
    on_startup = database.init_db
