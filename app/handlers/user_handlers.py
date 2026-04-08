from aiogram import Router, F, types, Bot # Bot qo'shildi
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from arq import create_pool
from arq.connections import RedisSettings

from config import Config
from database import get_from_cache, add_user, increment_stats, get_channels, get_setting
from app.utils.validators import extract_instagram_url
from app.services.downloader import DownloaderService

router = Router()

async def get_redis():
    if Config.REDIS_URL:
        return await create_pool(RedisSettings.from_dsn(Config.REDIS_URL))
    return await create_pool(RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT, password=Config.REDIS_PASSWORD))

async def check_subscription(user_id: int, bot: Bot): # types.Bot -> Bot bo'ldi
    channels = await get_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.chat_id, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(ch)
        except:
            not_subscribed.append(ch)
    return not_subscribed

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
        if message.chat.type in ['group', 'supergroup']: return
        return await message.answer("❌ Bu Instagram linki emas!")

    # Admin xabari emasligini tekshirish (agar admin link tashlasa ham tekshiruvdan o'tishi uchun)
    if not message.from_user.id in Config.ADMIN_IDS:
        not_subscribed = await check_subscription(message.from_user.id, message.bot)
        if not_subscribed:
            builder = InlineKeyboardBuilder()
            for ch in not_subscribed:
                builder.row(types.InlineKeyboardButton(text=ch.title, url=ch.url))
            builder.row(types.InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub"))
            return await message.answer("❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=builder.as_markup())

    await add_user(message.from_user.id, message.from_user.username)
    await increment_stats()

    url_hash = DownloaderService.get_url_hash(url)
    cached = await get_from_cache(url_hash)
    
    if cached and cached.file_type == 'video':
        bot_user = await message.bot.get_me()
        bot_username = bot_user.username
        
        extra_caption = await get_setting('custom_caption', "")
        caption_text = f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩"
        if extra_caption:
            caption_text += f"\n\n{extra_caption}"

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data="cached"))
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))

        return await message.reply_video(
            cached.file_id, 
            caption=caption_text,
            reply_markup=builder.as_markup()
        )

    wait_msg = await message.answer("⏳ Navbatga qo'shildi...")
    redis = await get_redis()
    await redis.enqueue_job('download_task', message.chat.id, url, 'video', wait_msg.message_id)

@router.callback_query(F.data == "check_sub")
async def check_sub_btn(callback: types.CallbackQuery):
    not_subscribed = await check_subscription(callback.from_user.id, callback.bot)
    if not_subscribed:
        await callback.answer("❌ Hali hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        await callback.message.delete()
        await callback.message.answer("✅ Raxmat! Endi Instagram linkini yuborishingiz mumkin.")

@router.callback_query(F.data == "cached")
async def handle_cached_callback(callback: types.CallbackQuery):
    await callback.answer("✅ Ushbu video bot keshida saqlangan!", show_alert=False)
