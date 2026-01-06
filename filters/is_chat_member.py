# filters/is_chat_member.py
from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram import Bot

class IsBotAdminInChat(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        if not message.forward_from_chat:
            return False
        
        chat_id = message.forward_from_chat.id
        try:
            member = await bot.get_chat_member(chat_id, bot.id)
            return member.status in ("administrator", "creator")
        except Exception:
            return False