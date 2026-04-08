import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import Config
from database import init_db
from app.handlers import user_handlers
from app.middlewares.throttling import ThrottlingMiddleware

# Logging o'rnatish
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def main():
    # 1. Ma'lumotlar bazasini inisializatsiya qilish
    await init_db()
    
    # 2. Bot va Dispatcher
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()

    # 3. Middleware qo'shish
    dp.message.middleware(ThrottlingMiddleware())

    # 4. Handlerlarni ulash
    dp.include_router(user_handlers.router)

    # 5. Polling boshlash
    print("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
