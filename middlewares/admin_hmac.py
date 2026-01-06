# middlewares/admin_hmac.py
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from core.security.hmac_signer import verify_signature

class AdminSecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли это callback data
        if not isinstance(event, CallbackQuery) or not event.data:
            return await handler(event, data)

        # Если префикс 'adm', значит это админ-панель
        # Формат: adm:action:id:sig
        if event.data.startswith("adm:"):
            parts = event.data.split(":")
            if len(parts) != 4:
                await event.answer("❌ Broken data", show_alert=True)
                return
            
            _, action, entity_id, sig = parts
            admin_id = event.from_user.id
            
            # ПРОВЕРКА ПОДПИСИ
            if not verify_signature(action, int(entity_id), admin_id, sig):
                print(f"[SECURITY ALERT] Bad Signature from user {admin_id}")
                await event.answer("⛔ Security Alert: Invalid Signature!", show_alert=True)
                return

        return await handler(event, data)