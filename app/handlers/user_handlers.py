import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from arq.connections import ArqRedis

from config import Config
from database import (
    get_from_cache,
    remove_from_cache,
    add_user,
    get_channels,
    get_setting
)
from app.utils.validators import extract_instagram_url
from app.services.downloader import DownloaderService

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
    builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_info.username}?startgroup=true"))
    
    await message.answer(
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "Men Instagramdan video, rasm va karusellarni yuklab beruvchi qulay botman.\n\n"
        "Yuklab olish uchun Instagram havolasini yuboring:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router.message(Command("admin"))
async def cmd_not_admin(message: types.Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    await message.answer(
        f"❌ Kechirasiz, siz admin emassiz.\nSizning ID: <code>{user_id}</code>",
        parse_mode="HTML"
    )

@router.message(F.text)
async def handle_message(message: types.Message, redis: ArqRedis):
    url = extract_instagram_url(message.text)
    if not url:
        if message.chat.type in ['group', 'supergroup']:
            return
        return await message.answer("❌ Bu to'g'ri Instagram havolasi emas!\nIltimos, post yoki reel havolasini yuboring.")

    user_id = message.from_user.id if message.from_user else message.chat.id
    username = message.from_user.username if message.from_user else None

    # Majburiy obunani tekshirish (Adminlar uchun tekshirilmaydi)
    if user_id not in Config.ADMIN_IDS:
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

        try:
            if cached.file_type == 'video':
                return await message.reply_video(cached.file_id, caption=caption_text, reply_markup=markup)
            elif cached.file_type == 'photo':
                return await message.reply_photo(cached.file_id, caption=caption_text, reply_markup=markup)
            elif cached.file_type == 'audio':
                return await message.reply_audio(cached.file_id, caption=caption_text, reply_markup=markup)
        except Exception as e:
            logging.warning(f"Keshdagi file_id yaroqsiz bo'lib qolgan ({e}). Qayta yuklanmoqda...")
            await remove_from_cache(url_hash)

    # Navbatga qo'shish
    wait_msg = await message.answer("⏳ Navbatga qo'shildi...")
    await redis.enqueue_job('download_task', message.chat.id, url, 'video', wait_msg.message_id)

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
        await callback.message.answer("✅ Rahmat! Endi Instagram havolasini yuborishingiz mumkin.")
