import os
import json
import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from arq.connections import ArqRedis
from arq.constants import default_queue_name
from aiogram.fsm.context import FSMContext

from config import Config
from database import (
    get_from_cache,
    remove_from_cache,
    add_user,
    get_channels,
    get_setting,
    add_to_cache,
    is_admin
)
from app.keyboards.admin_keyboards import admin_main_keyboard
from app.utils.validators import extract_media_url
from app.services.downloader import DownloaderService
from app.services.music_service import MusicService

router = Router()

async def check_subscription(user_id: int, bot: Bot):
    channels = await get_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.chat_id, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(ch)
        except TelegramForbiddenError:
            logging.warning(f"Bot kanalda admin emas yoki chiqarib yuborilgan: {ch.chat_id}")
            continue
        except TelegramBadRequest as e:
            err_text = str(e).lower()
            if "chat not found" in err_text or "user not found" in err_text:
                logging.warning(f"Kanal topilmadi: {ch.chat_id}")
                continue
            not_subscribed.append(ch)
        except Exception as e:
            logging.warning(f"Obunani tekshirishda xatolik ({ch.chat_id}): {e}")
            continue
    return not_subscribed

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    username = message.from_user.username if message.from_user else None
    await add_user(user_id, username)
    
    bot_info = await message.bot.get_me()
    builder = InlineKeyboardBuilder()
    
    # Foydalanuvchi admin yoki bot egasi ekanligini bazadan/ENV dan tekshirish
    is_user_admin = await is_admin(user_id)
    if is_user_admin:
        builder.row(types.InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin_back"))

    builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_info.username}?startgroup=true"))
    
    custom_start = await get_setting('start_message', "")
    if custom_start:
        start_text = custom_start
    else:
        start_text = (
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Men quyidagi platformalardan video, rasm va musiqalarni sifatli yuklab beruvchi botman:\n\n"
            "📸 <b>Instagram</b> (Reels, Post, Karusel)\n"
            "🎵 <b>TikTok</b> (Suv belgisiz video va slaydlar)\n"
            "📌 <b>Pinterest</b> (Video va rasmlar)\n"
            "🎬 <b>YouTube Shorts</b>\n"
            "🎧 <b>Musiqa topish</b> (Videodagi musiqalarni topish va yuklab olish)\n\n"
            "Yuklab olish uchun havola (link) yoki video yuboring:"
        )

    if is_user_admin:
        start_text += "\n\n👑 <b>Siz bot adminisiz!</b>\nAdmin panelni ochish uchun /admin buyrug'ini yuboring yoki quyidagi <b>🛠 Admin Panel</b> tugmasini bosing."
    
    try:
        await message.answer(
            start_text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logging.warning(f"Start xabari HTML formatida xatolik ({e}), xavfsiz matn yuborilmoqda")
        try:
            await message.answer(
                start_text,
                parse_mode=None,
                reply_markup=builder.as_markup()
            )
        except Exception:
            default_text = "👋 Assalomu alaykum!\n\nYuklab olish uchun havola (link) yuboring:"
            await message.answer(default_text, reply_markup=builder.as_markup())

@router.message(Command("admin", "panel"))
async def cmd_not_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if await is_admin(user_id):
        await state.clear()
        return await message.answer("🛠 <b>Admin panelga xush kelibsiz:</b>", parse_mode="HTML", reply_markup=admin_main_keyboard())

    await message.answer(
        f"❌ <b>Kechirasiz, siz bot admini emassiz!</b>\n\n"
        f"🆔 Sizning Telegram ID raqamingiz: <code>{user_id}</code>\n\n"
        f"💡 <b>Admin bo'lish uchun:</b>\n"
        f"Coolify panelingizda (Environment Variables bo'limida):\n"
        f"<code>ADMIN_IDS={user_id}</code>\n"
        f"o'zgaruvchisini qo'shing yoki mavjud admin <code>/addadmin {user_id}</code> yozsin.",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_") | (F.data == "admin_back") | (F.data == "add_channel") | F.data.startswith("del_ch:"))
async def unauthorized_admin_callback(callback: types.CallbackQuery):
    await callback.answer("❌ Siz bot admini emassiz!", show_alert=True)

@router.message(F.text)
async def handle_message(message: types.Message, redis: ArqRedis):
    parsed = extract_media_url(message.text)
    if not parsed:
        # Guruhlarda oddiy xabarlarga bot umuman aralashmaydi va indamaydi
        if message.chat.type in ['group', 'supergroup']:
            return
        # Faqat shaxsiy chatda xatolik bildirishnomasi beriladi
        return await message.answer(
            "❌ <b>Qo'llab-quvvatlanmaydigan havola!</b>\n\n"
            "Iltimos, quyidagi platformalardan birining havolasini yuboring:\n"
            "• 📸 <b>Instagram</b>\n"
            "• 🎵 <b>TikTok</b>\n"
            "• 📌 <b>Pinterest</b>\n"
            "• 🎬 <b>YouTube Shorts</b>",
            parse_mode="HTML"
        )

    url, platform = parsed
    user_id = message.from_user.id if message.from_user else message.chat.id
    username = message.from_user.username if message.from_user else None

    # Majburiy obunani tekshirish:
    # Faqat shaxsiy (private) chatda tekshiriladi, guruhlarni bezovta qilmaymiz
    if message.chat.type == 'private' and user_id not in Config.ADMIN_IDS:
        not_subscribed = await check_subscription(user_id, message.bot)
        if not_subscribed:
            builder = InlineKeyboardBuilder()
            for ch in not_subscribed:
                builder.row(types.InlineKeyboardButton(text=ch.title, url=ch.url))
            builder.row(types.InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub"))
            return await message.answer(
                "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=builder.as_markup()
            )

    await add_user(user_id, username)

    # Keshni tekshirish
    url_hash = DownloaderService.get_url_hash(url)
    cached = await get_from_cache(url_hash)
    
    if cached:
        bot_user = await message.bot.get_me()
        extra_caption = await get_setting('custom_caption', "")
        caption_text = f"❤️ @{bot_user.username} orqali yuklab olindi 🚀 📩"
        if extra_caption:
            caption_text += f"\n\n{extra_caption}"

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_user.username}?startgroup=true"))
        markup = builder.as_markup()

        # Video uchun maxsus klaviatura (Saqlash va Qo'shiqni yuklab olish bilan)
        v_builder = InlineKeyboardBuilder()
        v_builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save:{url_hash}"))
        v_builder.row(types.InlineKeyboardButton(text="📩 Qo'shiqni yuklab olish", callback_data=f"audio:{url_hash}"))
        v_builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_user.username}?startgroup=true"))
        video_markup = v_builder.as_markup()

        try:
            if cached.file_type == 'video':
                return await message.reply_video(cached.file_id, caption=caption_text, reply_markup=video_markup, supports_streaming=True)
            elif cached.file_type == 'photo':
                return await message.reply_photo(cached.file_id, caption=caption_text, reply_markup=markup)
            elif cached.file_type == 'audio':
                return await message.reply_audio(cached.file_id, caption=caption_text, reply_markup=markup)
        except Exception as e:
            logging.warning(f"Keshdagi file_id yaroqsiz ({e}). Qayta yuklanmoqda...")
            await remove_from_cache(url_hash)

    # Navbatga qo'shish (guruhda foydalanuvchining havolasiga javob (reply) qilib yuborishi uchun message.message_id uzatiladi)
    try:
        queue_size = await redis.zcard(default_queue_name)
    except Exception:
        queue_size = 0

    if queue_size > 0:
        wait_msg = await message.reply(f"⏳ So'rovingiz navbatga olindi (Sizdan oldin: {queue_size} ta so'rov)...")
    else:
        wait_msg = await message.reply("⏳ Yuklanmoqda...")

    await redis.enqueue_job(
        'download_task',
        message.chat.id,
        url,
        'video',
        wait_msg.message_id,
        message.message_id
    )

@router.callback_query(F.data.startswith("audio:"))
async def handle_audio_download(callback: types.CallbackQuery, redis: ArqRedis):
    url_hash = callback.data.split(":", 1)[1]
    cached = await get_from_cache(url_hash)
    if not cached or not cached.original_url:
        return await callback.answer("❌ Havola ma'lumotlari topilmadi.", show_alert=True)
    
    # 0. Redis keshdan qidiruv natijalarini tekshirish (o'ta tezkor javob uchun)
    music_cache_key = f"music_search:{url_hash}"
    try:
        cached_search = await redis.get(music_cache_key)
        if cached_search:
            raw_data = cached_search.decode('utf-8') if isinstance(cached_search, bytes) else cached_search
            data = json.loads(raw_data)
            music_info = data.get('music_info')
            tracks = data.get('tracks')
            if music_info and tracks:
                bot_user = await callback.bot.get_me()
                artist = music_info.get('artist', '')
                title = music_info.get('title', '')
                header = f"🎵 <b>{artist} — {title}</b>" if artist else f"🎵 <b>{title}</b>"
                lines = [header, ""]
                for idx, t in enumerate(tracks):
                    lines.append(f"{idx+1}. {t['title']} {t['duration_str']}")
                lines.append("")
                lines.append(f"❤️ @{bot_user.username} orqali istagan musiqangizni tez va oson toping! 🚀")
                text = "\n".join(lines)

                builder = InlineKeyboardBuilder()
                builder.row(types.InlineKeyboardButton(text="📼 Video", callback_data=f"show_vid:{url_hash}"))
                num_buttons = []
                for idx, t in enumerate(tracks):
                    num_buttons.append(types.InlineKeyboardButton(text=str(idx+1), callback_data=f"yt_audio:{t['id']}"))
                builder.row(*num_buttons)

                await callback.answer()
                return await callback.message.reply(text, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logging.warning(f"Keshdagi musiqani o'qishda xatolik: {e}")

    await callback.answer("🔍 Videodagi musiqa aniqlanmoqda...")
    status_msg = await callback.message.reply("🔍 Musiqa qidirilmoqda, kuting...")
    
    # 1. Musiqani aniqlash (metadata yoki Shazam orqali)
    music_service = MusicService()
    music_info = await music_service.get_music_info_from_url(cached.original_url)
    
    if music_info and music_info.get('title'):
        artist = music_info.get('artist', '')
        title = music_info.get('title', '')
        query = f"{artist} {title}".strip()
        tracks = await music_service.search_tracks(query, limit=5)
        
        if tracks:
            # Qidiruv natijasini Redis-ga 7 kunga keshga saqlash
            try:
                await redis.set(music_cache_key, json.dumps({'music_info': music_info, 'tracks': tracks}), ex=86400 * 7)
            except Exception as e:
                logging.warning(f"Musiqa natijasini keshga yozishda xatolik: {e}")

            bot_user = await callback.bot.get_me()
            header = f"🎵 <b>{artist} — {title}</b>" if artist else f"🎵 <b>{title}</b>"
            lines = [header, ""]
            for idx, t in enumerate(tracks):
                lines.append(f"{idx+1}. {t['title']} {t['duration_str']}")
            lines.append("")
            lines.append(f"❤️ @{bot_user.username} orqali istagan musiqangizni tez va oson toping! 🚀")
            text = "\n".join(lines)

            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="📼 Video", callback_data=f"show_vid:{url_hash}"))
            
            num_buttons = []
            for idx, t in enumerate(tracks):
                num_buttons.append(types.InlineKeyboardButton(text=str(idx+1), callback_data=f"yt_audio:{t['id']}"))
            builder.row(*num_buttons)
            
            return await status_msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    # 2. Agar musiqa nomi aniqlanmasa, videoning o'zidagi audioni olib berish (Fallback)
    audio_hash = DownloaderService.get_url_hash(cached.original_url + "_audio")
    cached_audio = await get_from_cache(audio_hash)
    if cached_audio:
        await status_msg.delete()
        bot_user = await callback.bot.get_me()
        return await callback.message.reply_audio(
            cached_audio.file_id,
            caption=f"❤️ @{bot_user.username} orqali yuklab olindi 🚀"
        )
        
    try:
        queue_size = await redis.zcard(default_queue_name)
    except Exception:
        queue_size = 0
    wait_text = f"⏳ Navbatga olindi (Navbatda: {queue_size} ta)..." if queue_size > 0 else "🎵 Video audiosi yuklanmoqda..."
    await status_msg.edit_text(wait_text)

    await redis.enqueue_job(
        'download_task',
        callback.message.chat.id,
        cached.original_url,
        'audio',
        status_msg.message_id,
        callback.message.message_id
    )

@router.callback_query(F.data.startswith("yt_audio:"))
async def handle_yt_audio_download(callback: types.CallbackQuery, redis: ArqRedis):
    yt_id = callback.data.split(":", 1)[1]
    cache_key = f"yt_{yt_id}"
    cached = await get_from_cache(cache_key)
    if cached:
        await callback.answer()
        bot_user = await callback.bot.get_me()
        return await callback.message.reply_audio(
            cached.file_id,
            caption=f"❤️ @{bot_user.username} orqali yuklab olindi 🚀"
        )

    await callback.answer("⏳ So'rovingiz navbatga qo'yildi...")

    try:
        queue_size = await redis.zcard(default_queue_name)
    except Exception:
        queue_size = 0

    wait_text = f"⏳ Navbatga olindi (Navbatda: {queue_size} ta)..." if queue_size > 0 else "🎵 Audio yuklanmoqda..."
    wait_msg = await callback.message.reply(wait_text)

    await redis.enqueue_job(
        'yt_audio_task',
        callback.message.chat.id,
        yt_id,
        wait_msg.message_id,
        callback.message.message_id
    )

@router.callback_query(F.data.startswith("save:"))
async def handle_save_media(callback: types.CallbackQuery):
    url_hash = callback.data.split(":", 1)[1]
    cached = await get_from_cache(url_hash)
    if not cached or not cached.file_id:
        return await callback.answer("❌ Fayl topilmadi.", show_alert=True)
    
    # Agar guruhda bo'lsa, foydalanuvchining shaxsiy chatiga nusxasini yuboramiz
    if callback.message.chat.type in ['group', 'supergroup']:
        try:
            bot_user = await callback.bot.get_me()
            extra_caption = await get_setting('custom_caption', "")
            caption = f"❤️ @{bot_user.username} orqali yuklab olindi 🚀"
            if extra_caption:
                caption += f"\n\n{extra_caption}"
            
            if cached.file_type == 'video':
                await callback.bot.send_video(callback.from_user.id, cached.file_id, caption=caption, supports_streaming=True)
            elif cached.file_type == 'photo':
                await callback.bot.send_photo(callback.from_user.id, cached.file_id, caption=caption)
            elif cached.file_type == 'audio':
                await callback.bot.send_audio(callback.from_user.id, cached.file_id, caption=caption)
            
            await callback.answer("✅ Video shaxsiy xabaringizga (lichka) yuborildi!", show_alert=True)
        except Exception:
            await callback.answer("⚠️ Bot sizga xabar yuborishi uchun avval botga kirib /start bosing!", show_alert=True)
    else:
        # Shaxsiy chatda bo'lsa
        await callback.answer("💾 Ushbu faylni saqlash uchun ustiga bosib 'Saqlangan xabarlar' (Saved Messages) ga yuborishingiz mumkin!", show_alert=True)

@router.callback_query(F.data.startswith("show_vid:"))
async def handle_show_video(callback: types.CallbackQuery):
    url_hash = callback.data.split(":", 1)[1]
    cached = await get_from_cache(url_hash)
    if not cached or cached.file_type != 'video':
        return await callback.answer("❌ Video topilmadi.", show_alert=True)

    await callback.answer()
    bot_user = await callback.bot.get_me()
    v_builder = InlineKeyboardBuilder()
    v_builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save:{url_hash}"))
    v_builder.row(types.InlineKeyboardButton(text="📩 Qo'shiqni yuklab olish", callback_data=f"audio:{url_hash}"))
    v_builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_user.username}?startgroup=true"))

    await callback.message.reply_video(
        cached.file_id,
        caption=f"❤️ @{bot_user.username} orqali yuklab olindi 🚀",
        reply_markup=v_builder.as_markup(),
        supports_streaming=True
    )

@router.message(F.video | F.video_note | F.audio | F.voice)
async def handle_direct_media(message: types.Message):
    if message.chat.type != 'private':
        return

    status_msg = await message.reply("🔍 Musiqa aniqlanmoqda, kuting...")
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id

    if not file_id:
        return await status_msg.edit_text("❌ Fayl qabul qilinmadi.")

    temp_path = f"{Config.DOWNLOAD_PATH}/probe_{file_id[:10]}_{message.message_id}.mp4"
    try:
        bot = message.bot
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, temp_path)

        music_service = MusicService()
        res = await music_service.recognize_audio(temp_path)
        if not res:
            return await status_msg.edit_text("❌ Kechirasiz, ushbu fayldan musiqa topilmadi.")

        artist = res.get('artist', '')
        title = res.get('title', '')
        query = f"{artist} {title}".strip()
        tracks = await music_service.search_tracks(query, limit=5)
        if not tracks:
            return await status_msg.edit_text(f"🎵 <b>{artist} — {title}</b> topildi, lekin yuklab olish uchun treklar mavjud emas.", parse_mode="HTML")

        bot_user = await bot.get_me()
        header = f"🎵 <b>{artist} — {title}</b>" if artist else f"🎵 <b>{title}</b>"
        lines = [header, ""]
        for idx, t in enumerate(tracks):
            lines.append(f"{idx+1}. {t['title']} {t['duration_str']}")
        lines.append("")
        lines.append(f"❤️ @{bot_user.username} orqali istagan musiqangizni tez va oson toping! 🚀")
        text = "\n".join(lines)

        builder = InlineKeyboardBuilder()
        num_buttons = []
        for idx, t in enumerate(tracks):
            num_buttons.append(types.InlineKeyboardButton(text=str(idx+1), callback_data=f"yt_audio:{t['id']}"))
        builder.row(*num_buttons)

        await status_msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logging.error(f"Media fayldan musiqa aniqlashda xatolik: {e}")
        await status_msg.edit_text("❌ Musiqani aniqlashda xatolik yuz berdi.")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@router.callback_query(F.data == "check_sub")
async def check_sub_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = await check_subscription(user_id, callback.bot)
    if not_subscribed:
        await callback.answer("❌ Hali hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("✅ Rahmat! Endi havola yuborishingiz mumkin.")
