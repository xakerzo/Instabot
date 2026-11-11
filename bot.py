import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from arq import create_pool

from config import Config, setup_environment, get_redis_settings
from database import init_db
from app.handlers import user_handlers, admin_handlers
from app.middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def main():
    # Papkalar va cookies sozlash
    setup_environment()
    
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    
    if not Config.BOT_TOKEN:
        logging.error("BOT_TOKEN ko'rsatilmagan! Iltimos, .env yoki Environment Variables ni to'ldiring.")
        return

    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Redis ulanish hovuzi (Connection Pool)
    redis_settings = get_redis_settings()
    logging.info(f"Redis-ga ulanmoqda: {redis_settings.host}:{redis_settings.port} (username='{redis_settings.username}', parol_mavjud={bool(redis_settings.password)})")
    redis_pool = await create_pool(redis_settings)
    dp["redis"] = redis_pool
    
    # Middleware-lar
    dp.message.middleware(ThrottlingMiddleware())
    
    # Handler-larni ulash
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
