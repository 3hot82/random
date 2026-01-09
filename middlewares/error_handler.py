from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from core.exceptions import error_handler


class ErrorMiddleware(BaseMiddleware):
    """
    Мидлварь для перехвата и обработки исключений
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # Получаем user_id из события
            user_id = None
            if hasattr(event, 'from_user') and event.from_user:
                user_id = event.from_user.id
            elif hasattr(event, 'user') and event.user:
                user_id = event.user.id
            
            # Определяем тип события
            event_type = type(event).__name__
            
            # Обрабатываем ошибку через централизованный обработчик
            await error_handler.handle_error(e, user_id, f"middleware_{event_type}")
            
            # В зависимости от типа ошибки можно принять разные меры
            # Для некоторых критических ошибок можно не пробрасывать дальше
            raise e