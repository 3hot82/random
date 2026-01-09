# filters/is_admin.py
from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import config


class IsAdmin(BaseFilter):
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        # Работает и для сообщений, и для колбэков
        user_id = obj.from_user.id
        return user_id in config.ADMIN_IDS