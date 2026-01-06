# keyboards/callback_data.py
from aiogram.filters.callback_data import CallbackData

class AdminAction(CallbackData, prefix="adm"):
    """
    Данные для админских кнопок.
    sig - это HMAC подпись.
    """
    action: str
    id: int
    sig: str

class JoinAction(CallbackData, prefix="join"):
    """
    Данные для кнопки участия.
    """
    giveaway_id: int