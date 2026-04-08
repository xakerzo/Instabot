from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from cachetools import TTLCache

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode: float = 2.0):
        self.cache = TTLCache(maxsize=10000, ttl=slow_mode)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, types.Message):
            return await handler(event, data)

        user_id = event.from_user.id
        if user_id in self.cache:
            return await event.answer("⚠️ Iltimos, biroz kutib turing (spam taqiqlangan).")

        self.cache[user_id] = True
        return await handler(event, data)
