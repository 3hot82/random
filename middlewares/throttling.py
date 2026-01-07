from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, rate_limit: float = 1.0):
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Работаем только с колбэками (кнопки) или командами
        user_id = event.from_user.id
        
        # Ключ анти-спама: throttle:USER_ID
        key = f"throttle:{user_id}"
        
        # Проверяем наличие ключа в Redis
        if await self.redis.get(key):
            # Если ключ есть, значит прошло меньше rate_limit секунд
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Не так быстро!", show_alert=True)
            return # Прерываем обработку, хендлер не запустится
            
        # Устанавливаем ключ с временем жизни (TTL) = rate_limit
        await self.redis.set(key, "1", ex=int(self.rate_limit))
        
        # Пропускаем дальше
        return await handler(event, data)