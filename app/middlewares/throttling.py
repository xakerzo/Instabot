import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from cachetools import TTLCache
from config import Config
from database import add_user
from app.utils.validators import is_supported_url

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode: float = 2.0):
        self.cache = TTLCache(maxsize=10000, ttl=slow_mode)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, types.Message):
            return await handler(event, data)

        user = getattr(event, 'from_user', None)
        if not user:
            return await handler(event, data)

        # Shaxsiy chatdagi har bir foydalanuvchini avtomatik bazaga kiritish (Broadcast va statistika uchun)
        if user.id > 0 and event.chat.type == 'private':
            try:
                await add_user(user.id, user.username)
            except Exception as e:
                logging.debug(f"Userni bazaga kiritishda xatolik ({user.id}): {e}")

        # Adminlarga throttling ta'sir qilmaydi
        if user.id in Config.ADMIN_IDS:
            return await handler(event, data)

        # Guruhlarda oddiy suhbatlashayotgan odamlarga xalal bermaslik
        # Throttling faqat botga buyruq yoki media havolasi yuborilgandagina qo'llanadi
        if event.chat.type in ['group', 'supergroup']:
            text = event.text or event.caption or ""
            if not (text.startswith('/') or is_supported_url(text)):
                return await handler(event, data)

        user_id = user.id
        if user_id in self.cache:
            try:
                await event.answer("⚠️ Iltimos, biroz kuting (spam taqiqlangan).")
            except Exception:
                pass
            return

        self.cache[user_id] = True
        return await handler(event, data)
