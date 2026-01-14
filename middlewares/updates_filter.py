import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)

class UpdatesFilterMiddleware(BaseMiddleware):
    """
    Фильтрует сообщения, которые пришли, пока бот лежал.
    Пропускает только:
    1. "Свежие" сообщения (моложе TTL).
    2. Платежи (successful_payment) - они важны всегда.
    """
    
    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # Мы фильтруем только Message, так как CallbackQuery (кнопки) обычно 
        # не имеют поля date на верхнем уровне и их лучше обработать (или они сами протухнут у Telegram)
        if not isinstance(event, Message):
            return await handler(event, data)

        # Всегда пропускаем платежи, даже если бот лежал час
        if event.successful_payment or (hasattr(event, 'invoice_payload') and event.invoice_payload):
            return await handler(event, data)

        # Проверка времени
        # Telegram присылает дату в UTC (aware или naive зависит от версии, приводим к aware UTC)
        msg_date = event.date
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        delta = (now - msg_date).total_seconds()

        # Если сообщение старее TTL (например, 60 сек)
        if delta > self.ttl:
            logger.warning(f"⏩ Skipped old update from user {event.from_user.id} (delay: {int(delta)}s)")
            return  # Просто выходим, не вызывая handler -> сообщение игнорируется
            
        return await handler(event, data)