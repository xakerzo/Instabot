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
from app.utils.video_processor import compress_video, get_video_info
import database
import ffmpeg

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

async def download_task(ctx, user_id: int, url: str, mode: str = 'video', message_id: Optional[int] = None, reply_to_id: Optional[int] = None):
    bot: Bot = ctx.get('bot') or Bot(token=Config.BOT_TOKEN)
    downloader: DownloaderService = ctx.get('downloader') or DownloaderService()
    
    url_hash = downloader.get_url_hash(url)
    files_to_clean: List[str] = []
    
    try:
        bot_user = await bot.get_me()
        bot_username = bot_user.username

        # Agar navbatda turgan bo'lsa, yuklash boshlanganini bildirish
        if message_id:
            try:
                await bot.edit_message_text("⏳ Yuklab olinmoqda...", chat_id=user_id, message_id=message_id)
            except Exception:
                pass

        # Tezkor media yuklash
        result = await downloader.download(url, mode)
        for f in result.get('files', []):
            if f and f not in files_to_clean:
                files_to_clean.append(f)

        extra_caption = await database.get_setting('custom_caption', "")
        caption_text = f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩"
        if extra_caption:
            caption_text += f"\n\n{extra_caption}"

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save:{url_hash}"))
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))
        markup = builder.as_markup()

        media_type = result.get('type', 'video')

        if media_type == 'video':
            file_path = result['file_path']
            meta = get_video_info(file_path)
            codec = meta.get('codec_name', '').lower()
            
            # Agar format .mp4 bo'lmasa (masalan .webm) yoki video kodeki h264 bo'lmasa (masalan av01, vp9),
            # Telegram yaxshi qabul qilishi va oppoq kadr chiqmasligi uchun .mp4 (h264+aac) ga o'giramiz
            needs_transcode = False
            if file_path and os.path.exists(file_path):
                if not file_path.lower().endswith('.mp4'):
                    needs_transcode = True
                elif codec and codec not in ['h264', 'avc1']:
                    needs_transcode = True

            if needs_transcode and file_path and os.path.exists(file_path):
                mp4_target = os.path.splitext(file_path)[0] + "_std.mp4"
                try:
                    (
                        ffmpeg
                        .input(file_path)
                        .output(
                            mp4_target,
                            vcodec='libx264',
                            acodec='aac',
                            pix_fmt='yuv420p',
                            preset='veryfast',
                            movflags='+faststart'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    if os.path.exists(mp4_target) and os.path.getsize(mp4_target) > 0:
                        files_to_clean.append(mp4_target)
                        file_path = mp4_target
                        # Qayta metadata olish
                        meta = get_video_info(file_path)
                except Exception as ex:
                    logging.warning(f"Video formatini MP4 ga o'tkazishda xatolik: {ex}")

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
                    meta = get_video_info(file_path)

            if file_size > 50 * 1024 * 1024:
                await bot.send_message(user_id, "⚠️ Video hajmi Telegram limitidan (50MB) katta bo'lgani uchun yuborib bo'lmadi.")
                return

            # Video uchun metadata va chiroyli preview thumbnail olish
            duration = meta['duration'] or result.get('duration', 0)
            width = meta['width']
            height = meta['height']
            thumb_file = None
            if meta['thumb_path']:
                files_to_clean.append(meta['thumb_path'])
                thumb_file = types.FSInputFile(meta['thumb_path'])

            # Video tagidagi tugmalar: Saqlash, Qo'shiqni yuklab olish va Guruhga qo'shish
            v_builder = InlineKeyboardBuilder()
            v_builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save:{url_hash}"))
            v_builder.row(types.InlineKeyboardButton(text="📩 Qo'shiqni yuklab olish", callback_data=f"audio:{url_hash}"))
            v_builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))
            video_markup = v_builder.as_markup()

            sent_msg = await bot.send_video(
                chat_id=user_id,
                video=types.FSInputFile(file_path),
                duration=duration,
                width=width,
                height=height,
                thumbnail=thumb_file,
                supports_streaming=True,
                caption=caption_text,
                reply_to_message_id=reply_to_id,
                reply_markup=video_markup
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
                reply_to_message_id=reply_to_id,
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
                    meta = get_video_info(f_path)
                    thumb_f = None
                    if meta['thumb_path']:
                        files_to_clean.append(meta['thumb_path'])
                        thumb_f = types.FSInputFile(meta['thumb_path'])
                    media_group.append(types.InputMediaVideo(
                        media=types.FSInputFile(f_path),
                        caption=cap,
                        duration=meta['duration'],
                        width=meta['width'],
                        height=meta['height'],
                        thumbnail=thumb_f,
                        supports_streaming=True
                    ))
                else:
                    media_group.append(types.InputMediaPhoto(media=types.FSInputFile(f_path), caption=cap))
            
            if media_group:
                chunks = [media_group[i:i + 10] for i in range(0, len(media_group), 10)]
                for c_idx, chunk in enumerate(chunks):
                    r_id = reply_to_id if c_idx == 0 else None
                    await bot.send_media_group(chat_id=user_id, media=chunk, reply_to_message_id=r_id)
                await bot.send_message(chat_id=user_id, text=f"❤️ @{bot_username} orqali yuklab olindi 🚀", reply_markup=markup, reply_to_message_id=reply_to_id)

        elif media_type == 'audio':
            file_path = result['file_path']
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            sent_msg = await bot.send_audio(
                chat_id=user_id,
                audio=types.FSInputFile(file_path),
                caption=caption_text,
                title=result.get('title', 'Audio'),
                reply_to_message_id=reply_to_id,
                reply_markup=markup
            )
            if sent_msg and sent_msg.audio:
                await database.add_to_cache(url_hash, sent_msg.audio.file_id, 'audio', file_size, original_url=url)
                audio_hash = downloader.get_url_hash(url + "_audio")
                if audio_hash != url_hash:
                    await database.add_to_cache(audio_hash, sent_msg.audio.file_id, 'audio', file_size, original_url=url)

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

async def yt_audio_task(ctx, chat_id: int, yt_id: str, message_id: Optional[int] = None, reply_to_id: Optional[int] = None):
    bot: Bot = ctx.get('bot') or Bot(token=Config.BOT_TOKEN)
    cache_key = f"yt_{yt_id}"
    
    # 1. Keshni tekshirish
    cached = await database.get_from_cache(cache_key)
    if cached:
        bot_user = await bot.get_me()
        try:
            await bot.send_audio(
                chat_id=chat_id,
                audio=cached.file_id,
                caption=f"❤️ @{bot_user.username} orqali yuklab olindi 🚀",
                reply_to_message_id=reply_to_id
            )
        except Exception:
            pass
        if message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
        return

    # 2. Worker yuklab olishni boshladi
    if message_id:
        try:
            await bot.edit_message_text("🎵 Audio yuklanmoqda...", chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

    from app.services.music_service import MusicService
    music_service = MusicService()
    res = await music_service.download_track(yt_id)
    
    if not res or not os.path.exists(res.get('file_path', '')):
        if message_id:
            try:
                await bot.edit_message_text("❌ Musiqani yuklab bo'lmadi.", chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
        return

    file_path = res['file_path']
    try:
        bot_user = await bot.get_me()
        sent_audio = await bot.send_audio(
            chat_id=chat_id,
            audio=types.FSInputFile(file_path),
            title=res.get('title'),
            performer=res.get('artist'),
            caption=f"❤️ @{bot_user.username} orqali yuklab olindi 🚀",
            reply_to_message_id=reply_to_id
        )
        if sent_audio and sent_audio.audio:
            await database.add_to_cache(
                cache_key,
                sent_audio.audio.file_id,
                'audio',
                os.path.getsize(file_path),
                original_url=f"https://www.youtube.com/watch?v={yt_id}"
            )
    except Exception as ex:
        logging.error(f"Audio yuborishda xatolik: {ex}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
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
    functions = [download_task, yt_audio_task]
    redis_settings = get_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 15          # Bir vaqtda 15 ta parallel yuklash (ortiqchalari Redis navbatida tartib bilan kutadi)
    job_timeout = 180       # 3 daqiqadan oshgan qotib qolgan vazifalarni to'xtatish
    max_tries = 1          # Xatolik bo'lsa navbatni tiqib tashlamaslik uchun 1 marta bajarish
    keep_result = 60       # Natijalarni Redis-da faqat 60 soniya saqlash
