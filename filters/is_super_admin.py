from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import config


class IsSuperAdmin(BaseFilter):
    """
    Фильтр для проверки, является ли пользователь супер-администратором.
    В текущей реализации супер-администратором считается первый администратор из списка.
    """
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        user_id = obj.from_user.id
        # Супер-администратор - это первый администратор из списка
        super_admin_id = config.ADMIN_IDS[0] if config.ADMIN_IDS else None
        return user_id == super_admin_id


class IsAdmin(BaseFilter):
    """
    Фильтр для проверки, является ли пользователь администратором.
    """
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        # Работает и для сообщений, и для колбэков
        user_id = obj.from_user.id
        return user_id in config.ADMIN_IDS