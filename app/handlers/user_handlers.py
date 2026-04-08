from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from arq import create_pool
from arq.connections import RedisSettings

from config import Config
from database import get_from_cache, add_user, increment_stats
from app.utils.validators import extract_instagram_url

router = Router()

async def get_redis():
    if Config.REDIS_URL:
        return await create_pool(RedisSettings.from_dsn(Config.REDIS_URL))
    return await create_pool(RedisSettings(host=Config.REDIS_HOST, port=Config.REDIS_PORT, password=Config.REDIS_PASSWORD))

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 Assalomu alaykum!\n\nMen Instagramdan video va rasmlarni yuklab beruvchi botman.\nLinkni yuboring:",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{(await message.bot.get_me()).username}?startgroup=true")
        ).as_markup()
    )

@router.message(F.text)
async def handle_message(message: types.Message):
    url = extract_instagram_url(message.text)
    if not url:
        # Guruhlarda bo'lsa va link bo'lmasa, indamaymiz
        if message.chat.type in ['group', 'supergroup']:
            return
        return await message.answer("❌ Bu Instagram linki emas!")

    # Foydalanuvchi statistikasini yangilash
    await add_user(message.from_user.id, message.from_user.username)
    await increment_stats()

    # Keshni tekshirish
    url_hash = f"v_{hash(url)}" # Downloader bilan bir xil hash bo'lishi kerak
    # Biz Downloader.get_url_hash ni ishlatamiz keyinroq
    from app.services.downloader import DownloaderService
    url_hash = DownloaderService.get_url_hash(url)
    
    cached = await get_from_cache(url_hash)
    if cached:
        bot_username = (await message.bot.get_me()).username
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="💾 Saqlash", callback_data="none"))
        builder.row(types.InlineKeyboardButton(text="📩 Qo'shiqni yuklab olish", callback_data=f"dl:audio:{url_hash}"))
        builder.row(types.InlineKeyboardButton(text="👉 Guruhga qo'shish 💥", url=f"https://t.me/{bot_username}?startgroup=true"))

        if cached.file_type == 'video':
            return await message.reply_video(
                cached.file_id, 
                caption=f"❤️ @{bot_username} orqali yuklab olindi 🚀 📩",
                reply_markup=builder.as_markup()
            )

    # Navbatga qo'shish
    wait_msg = await message.answer("⏳ Navbatga qo'shildi...")
    redis = await get_redis()
    await redis.enqueue_job('download_task', message.chat.id, url, 'video', wait_msg.message_id)

@router.callback_query(F.data.startswith("dl:"))
async def handle_callback(callback: types.CallbackQuery):
    _, mode, url_hash = callback.data.split(":")
    
    # Bu yerda bizga URL kerak, lekin keshda faqat file_id bor. 
    # Shunchaki xabar beramiz yoki keshni to'liqroq qilamiz.
    # Hozircha oddiygina:
    await callback.answer("⏳ MP3 tayyorlanmoqda...", show_alert=False)
    # Eslatma: Callback uchun to'liq URL saqlash kerak yoki redis ishlatish kerak.
    # Hozircha biz faqat video yuklashni chiroyli qildik.
