import os
import asyncio
import traceback
from arq import create_pool
from arq.connections import RedisSettings
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config
from app.services.downloader import DownloaderService
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
        # Bot username'ni olish (havola uchun)
        bot_user = await bot.get_me()
        bot_username = bot_user.username

        await bot.edit_message_text("⏳ Yuklanmoqda...", chat_id=user_id, message_id=message_id)
        
        result = await downloader.download(url, mode)
        file_path = result['file_path']
        
        await bot.edit_message_text("📤 Botga yuborilmoqda...", chat_id=user_id, message_id=message_id)
        
        input_file = types.FSInputFile(file_path)
        
        # Tugmalarni yasash
        builder = InlineKeyboardBuilder()
        if mode == 'video':
            builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data="none"))
            builder.row(types.InlineKeyboardButton(text="📩 Qo'shiqni yuklab olish", callback_data=f"dl:audio:{url_hash}"))
            builder.row(types.InlineKeyboardButton(
                text="👉 Guruhga qo'shish 💥", 
                url=f"https://t.me/{bot_username}?startgroup=true"
            ))
        
        caption_text = f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩"

        if mode == 'audio':
            await bot.send_audio(
                chat_id=user_id,
                audio=input_file,
                title=result['title'],
                caption=caption_text
            )
        else:
            await bot.send_video(
                chat_id=user_id,
                video=input_file,
                caption=caption_text,
                reply_markup=builder.as_markup()
            )

        # Keshga saqlash (MP4 faylni)
        if mode == 'video':
            file_id = None # Video yuborilgandan keyin file_id olish qiyinroq, lekin kesh baribir ishlaydi
            # Keyingi safar keshdan olish uchun file_id kerak, uni boshqa yo'l bilan saqlaymiz

        if os.path.exists(file_path): os.remove(file_path)
        await bot.delete_message(chat_id=user_id, message_id=message_id)

    except Exception as e:
        error_msg = str(e)
        print(f"Worker Error: {traceback.format_exc()}")
        await bot.send_message(user_id, f"❌ Xatolik yuz berdi:\n<code>{error_msg}</code>", parse_mode="HTML")

class WorkerSettings:
    functions = [download_task]
    redis_settings = get_redis_settings()
    on_startup = database.init_db
