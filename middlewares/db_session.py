# middlewares/db_session.py
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database import async_session_maker
from core.exceptions import error_handler


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            async with session.begin():  # Начинаем транзакцию
                try:
                    data["session"] = session
                    result = await handler(event, data)
                    # commit будет выполнен автоматически при выходе из блока if no exception
                    return result
                except Exception as e:
                    # Откатываем транзакцию в случае ошибки
                    await session.rollback()
                    # Получаем user_id из события
                    user_id = None
                    if hasattr(event, 'from_user') and event.from_user:
                        user_id = event.from_user.id
                    elif hasattr(event, 'user') and event.user:
                        user_id = event.user.id
                    
                    # Обрабатываем ошибку через централизованный обработчик
                    await error_handler.handle_error(e, user_id, "db_session_middleware")
                    raise e
