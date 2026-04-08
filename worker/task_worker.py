import os
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from aiogram import Bot
from config import Config
from app.services.downloader import DownloaderService
from app.utils.video_processor import compress_video
import database

# Bot instance worker uchun (javob yuborishga)
bot = Bot(token=Config.BOT_TOKEN)
downloader = DownloaderService()

async def download_task(ctx, user_id: int, url: str, mode: str = 'video', message_id: int = None):
    """Asosiy yuklash vazifasi"""
    url_hash = downloader.get_url_hash(url)
    
    try:
        # 1. Progress xabari
        await bot.edit_message_text("⏳ Yuklash boshlandi...", chat_id=user_id, message_id=message_id)
        
        # 2. Yuklab olish
        result = await downloader.download(url, mode)
        file_path = result['file_path']
        
        # 3. Agar video juda katta bo'lsa - siqish (faqat video uchun)
        if mode == 'video' and result['file_size'] > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
            await bot.edit_message_text("⚙️ Video hajmi katta, optimizatsiya qilinmoqda...", chat_id=user_id, message_id=message_id)
            file_path = compress_video(file_path)

        # 4. Yuborish
        await bot.edit_message_text("📤 Botga yuklanmoqda...", chat_id=user_id, message_id=message_id)
        
        sent_msg = None
        if mode == 'audio':
            sent_msg = await bot.send_audio(
                chat_id=user_id,
                audio=os.path.abspath(file_path),
                title=result['title'],
                duration=result['duration']
            )
        else:
            sent_msg = await bot.send_video(
                chat_id=user_id,
                video=os.path.abspath(file_path),
                caption=f"✅ {result['title']}\n\n🤖 @YourBot",
                duration=result['duration']
            )

        # 5. Keshga saqlash (file_id orqali)
        if sent_msg:
            file_id = sent_msg.video.file_id if mode == 'video' else sent_msg.audio.file_id
            await database.add_to_cache(
                url_hash=url_hash,
                file_id=file_id,
                media_type=mode,
                file_size=os.path.getsize(file_path)
            )

        # 6. Tozalash (faylni o'chirish)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await bot.delete_message(chat_id=user_id, message_id=message_id)

    except Exception as e:
        print(f"Worker Error: {e}")
        await bot.send_message(user_id, f"❌ Xatolik yuz berdi: {str(e)[:100]}")

class WorkerSettings:
    functions = [download_task]
    redis_settings = RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT)
    on_startup = database.init_db # Baza bilan bog'lanish
