from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
from config import config
import logging

logger = logging.getLogger('admin')


class IsAdmin(Filter):
    def __init__(self):
        super().__init__()
    
    async def __call__(self, obj: Message | CallbackQuery, **kwargs) -> bool:
        user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
        
        # Используем глобальный config объект
        is_admin = user_id in config.ADMIN_IDS
        if is_admin:
            logger.info(f"Admin {user_id} accessed admin panel")
        else:
            logger.warning(f"Unauthorized access attempt to admin panel by user {user_id}")
        
        return is_admin