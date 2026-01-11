from typing import Callable, Dict, Any

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.methods import AnswerCallbackQuery
from aiogram.fsm.context import FSMContext

from utils.rate_limiter import admin_rate_limiter


class AdminRateLimitMiddleware:
    """
    Middleware для проверки рейт-лимита администратора
    """
    async def __call__(
        self,
        handler: Callable,
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем рейт-лимит для администратора
        if not admin_rate_limiter.is_allowed(event.from_user.id):
            reset_time = admin_rate_limiter.get_reset_time(event.from_user.id)
            # Отправляем ответ на коллбэк
            await event.answer(f"❌ Слишком много запросов. Попробуйте через {int(reset_time)} сек.", show_alert=True)
            return
        
        # Если всё в порядке, продолжаем обработку
        return await handler(event, data)