import os
import time
import asyncio
import logging
from typing import List, Optional
from arq.connections import RedisSettings
from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import Config, setup_environment, get_redis_settings
from app.services.downloader import DownloaderService
from app.utils.video_processor import compress_video
import database

def cleanup_download_folder(folder_path: str, max_age_seconds: int = 600):
    """
    Downloads papkasini tekshirib, eski yoki qolib ketgan fayllarni tozalaydi.
    Server diski to'lib qolmasligini kafolatlaydi.
    """
    if not os.path.exists(folder_path):
        return
    now = time.time()
    for fname in os.listdir(folder_path):
        fpath = os.path.join(folder_path, fname)
        if os.path.isfile(fpath):
            try:
                # Chala fayllar (.part, .temp) yoki muddati o'tgan fayllar
                if fname.endswith(('.part', '.temp', '.ytdl')) or (now - os.path.getmtime(fpath) > max_age_seconds):
                    os.remove(fpath)
                    logging.info(f"Eski fayl tozalandi: {fpath}")
            except Exception as e:
                logging.warning(f"Faylni tozalashda xatolik ({fpath}): {e}")

async def download_task(ctx, user_id: int, url: str, mode: str = 'video', message_id: Optional[int] = None):
    bot: Bot = ctx.get('bot') or Bot(token=Config.BOT_TOKEN)
    downloader: DownloaderService = ctx.get('downloader') or DownloaderService()
    
    url_hash = downloader.get_url_hash(url)
    files_to_clean: List[str] = []
    
    try:
        # Xabar holatini yangilash
        if message_id:
            try:
                await bot.edit_message_text("⏳ Yuklanmoqda...", chat_id=user_id, message_id=message_id)
            except TelegramBadRequest:
                pass

        bot_user = await bot.get_me()
        bot_username = bot_user.username

        # Media yuklash
        result = await downloader.download(url, mode)
        for f in result.get('files', []):
            if f and f not in files_to_clean:
                files_to_clean.append(f)

        if message_id:
            try:
                await bot.edit_message_text("📤 Botga yuborilmoqda...", chat_id=user_id, message_id=message_id)
            except TelegramBadRequest:
                pass

        extra_caption = await database.get_setting('custom_caption', "")
        caption_text = f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩"
        if extra_caption:
            caption_text += f"\n\n{extra_caption}"

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))
        markup = builder.as_markup()

        media_type = result.get('type', 'video')

        if media_type == 'video':
            file_path = result['file_path']
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            # Agar 50MB dan katta bo'lsa, siqish
            if file_size > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
                if message_id:
                    try:
                        await bot.edit_message_text("⏳ Video hajmi katta, sifat saqlangan holda siqilmoqda...", chat_id=user_id, message_id=message_id)
                    except TelegramBadRequest:
                        pass
                
                compressed_path = compress_video(file_path, Config.MAX_FILE_SIZE_MB)
                if compressed_path != file_path:
                    files_to_clean.append(compressed_path)
                    file_path = compressed_path
                    file_size = os.path.getsize(file_path)

            if file_size > 50 * 1024 * 1024:
                await bot.send_message(user_id, "⚠️ Video hajmi Telegram limitidan (50MB) katta bo'lgani uchun yuborib bo'lmadi.")
                return

            sent_msg = await bot.send_video(
                chat_id=user_id,
                video=types.FSInputFile(file_path),
                caption=caption_text,
                reply_markup=markup
            )
            if sent_msg and sent_msg.video:
                await database.add_to_cache(url_hash, sent_msg.video.file_id, 'video', file_size, original_url=url)

        elif media_type == 'photo':
            file_path = result['file_path']
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            sent_msg = await bot.send_photo(
                chat_id=user_id,
                photo=types.FSInputFile(file_path),
                caption=caption_text,
                reply_markup=markup
            )
            if sent_msg and sent_msg.photo:
                await database.add_to_cache(url_hash, sent_msg.photo[-1].file_id, 'photo', file_size, original_url=url)

        elif media_type == 'album':
            items = result.get('items', [])
            media_group = []
            for idx, item in enumerate(items):
                cap = caption_text if idx == 0 else None
                f_path = item['path']
                if item['type'] == 'video':
                    if os.path.getsize(f_path) > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
                        comp_path = compress_video(f_path, Config.MAX_FILE_SIZE_MB)
                        if comp_path != f_path:
                            files_to_clean.append(comp_path)
                            f_path = comp_path
                    media_group.append(types.InputMediaVideo(media=types.FSInputFile(f_path), caption=cap))
                else:
                    media_group.append(types.InputMediaPhoto(media=types.FSInputFile(f_path), caption=cap))
            
            if media_group:
                chunks = [media_group[i:i + 10] for i in range(0, len(media_group), 10)]
                for chunk in chunks:
                    await bot.send_media_group(chat_id=user_id, media=chunk)
                await bot.send_message(chat_id=user_id, text=f"❤️ @{bot_username} orqali yuklab olindi 🚀", reply_markup=markup)

        elif media_type == 'audio':
            file_path = result['file_path']
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            sent_msg = await bot.send_audio(
                chat_id=user_id,
                audio=types.FSInputFile(file_path),
                caption=caption_text,
                title=result.get('title', 'Audio'),
                reply_markup=markup
            )
            if sent_msg and sent_msg.audio:
                await database.add_to_cache(url_hash, sent_msg.audio.file_id, 'audio', file_size, original_url=url)

        # Muvaffaqiyatli yuklanganda statistika oshiriladi
        await database.increment_stats('total_downloads')

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Download task error for {url}: {error_msg}")
        
        user_message = "❌ Yuklab olishda xatolik yuz berdi."
        if "empty media response" in error_msg.lower() or "private" in error_msg.lower():
            user_message = "❌ Bu post yopiq (private) profilga tegishli yoki o'chirib tashlangan. Bot faqat ochiq postlarni yuklay oladi."
        elif "rate-limit" in error_msg.lower() or "login required" in error_msg.lower():
            user_message = "⚠️ Platforma cheklovi yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring."
        elif "file is too big" in error_msg.lower():
            user_message = "⚠️ Fayl hajmi juda katta bo'lgani uchun uni Telegram orqali yuborib bo'lmadi."

        try:
            await bot.send_message(user_id, user_message)
        except Exception:
            pass

    finally:
        # 1. Vazifada yaratilgan barcha fayllarni darhol diskdan 100% tozalash
        for f in files_to_clean:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    logging.info(f"Vaqtinchalik fayl serverdan tozalandi: {f}")
                except Exception as ex:
                    logging.warning(f"Faylni o'chirishda xatolik ({f}): {ex}")
                    
        # 2. Xavfsizlik uchun qoldiq fayllarni tozalash (serverni to'lib ketishidan saqlash)
        cleanup_download_folder(Config.DOWNLOAD_PATH, max_age_seconds=600)
                    
        # 3. Kutilayotgan xabarni o'chirish
        if message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
            except Exception:
                pass

async def startup(ctx):
    setup_environment()
    await database.init_db()
    # Ishga tushganda eski qoldiq fayllarni darhol tozalash
    cleanup_download_folder(Config.DOWNLOAD_PATH, max_age_seconds=0)
    ctx['bot'] = Bot(token=Config.BOT_TOKEN)
    ctx['downloader'] = DownloaderService()
    logging.info("Worker muvaffaqiyatli ishga tushdi va disk tozalandi")

async def shutdown(ctx):
    bot: Bot = ctx.get('bot')
    if bot:
        await bot.session.close()
    logging.info("Worker to'xtatildi")

class WorkerSettings:
    functions = [download_task]
    redis_settings = get_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
