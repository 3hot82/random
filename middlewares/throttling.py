# middlewares/throttling.py
import time
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from redis.asyncio import Redis

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, rate_limit: float = 1.0):
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
            
        user_id = event.from_user.id
        key = f"throttle:{user_id}"
        
        # Простая проверка: если ключ есть, значит спам
        if await self.redis.get(key):
            await event.answer("⏳ Не так быстро!", show_alert=True)
            return
            
        # Ставим ключ на 1 секунду
        await self.redis.set(key, "1", ex=int(self.rate_limit))
        
        return await handler(event, data)