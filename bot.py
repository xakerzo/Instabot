import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from config import Config
from database import init_db
from app.handlers import user_handlers, admin_handlers # admin_handlers qo'shildi
from app.middlewares.throttling import ThrottlingMiddleware

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def main():
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    
    # Yuklamalar uchun papka yaratish
    os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
    
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Middleware-lar
    dp.message.middleware(ThrottlingMiddleware())
    
    # Handler-larni ulash
    dp.include_router(admin_handlers.router) # Admin handler birinchi turishi kerak
    dp.include_router(user_handlers.router)
    
    logging.info("Bot ishga tushmoqda...")
    
    # Eski xabarlarni o'tkazib yuborish va pollingni boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
