import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from arq import create_pool
from arq.connections import RedisSettings

from config import Config, setup_environment
from database import init_db
from app.handlers import user_handlers, admin_handlers
from app.middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

def get_redis_settings() -> RedisSettings:
    if Config.REDIS_URL:
        return RedisSettings.from_dsn(Config.REDIS_URL)
    return RedisSettings(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        password=Config.REDIS_PASSWORD
    )

async def main():
    # Papkalar va cookies sozlash
    setup_environment()
    
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    
    if not Config.BOT_TOKEN:
        logging.error("BOT_TOKEN ko'rsatilmagan! Iltimos, .env faylini to'ldiring.")
        return

    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Redis ulanish hovuzi (Connection Pool) - butun bot uchun bitta yaratiladi
    redis_settings = get_redis_settings()
    redis_pool = await create_pool(redis_settings)
    dp["redis"] = redis_pool
    
    # Middleware-lar
    dp.message.middleware(ThrottlingMiddleware())
    
    # Handler-larni ulash (Admin doim birinchi bo'lishi kerak)
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    
    logging.info("Bot muvaffaqiyatli ishga tushmoqda...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logging.info("Resurslar tozalanmoqda va ulanishlar yopilmoqda...")
        await redis_pool.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
