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
        bot_user = await bot.get_me()
        bot_username = bot_user.username

        await bot.edit_message_text("⏳ Yuklanmoqda...", chat_id=user_id, message_id=message_id)
        
        result = await downloader.download(url, 'video')
        file_path = result['file_path']
        
        await bot.edit_message_text("📤 Botga yuborilmoqda...", chat_id=user_id, message_id=message_id)
        
        input_file = types.FSInputFile(file_path)
        
        extra_caption = await database.get_setting('custom_caption', "")
        caption_text = f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩"
        if extra_caption:
            caption_text += f"\n\n{extra_caption}"

        # Videoni yuborish
        sent_msg = await bot.send_video(
            chat_id=user_id,
            video=input_file,
            caption=caption_text
        )
        
        # Tugmalar (file_id olgandan keyin ularni qo'shamiz)
        if sent_msg and sent_msg.video:
            file_id = sent_msg.video.file_id
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save:{file_id}"))
            builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))
            
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=sent_msg.message_id,
                reply_markup=builder.as_markup()
            )
            
            # Keshga saqlash
            await database.add_to_cache(url_hash, file_id, 'video', os.path.getsize(file_path), original_url=url)

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
