# keyboards/inline/participation.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def join_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    """Кнопка под постом в канале"""
    url = f"https://t.me/{bot_username}?start=gw_{giveaway_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать 🎁", url=url)]
    ])

def check_subscription_kb(gw_id: int, channels: list) -> InlineKeyboardMarkup:
    """
    Клавиатура, которую видит пользователь в ЛС, если не подписан.
    channels: список словарей {'title': str, 'link': str}
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки каналов
    for ch in channels:
        builder.button(text=f"📢 {ch['title']}", url=ch['link'])
    
    # Кнопка проверки (Callback!)
    builder.button(text="🔄 Я подписался", callback_data=f"check_sub:{gw_id}")
    
    builder.adjust(1)
    return builder.as_markup()

def results_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start=res_{giveaway_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Проверить результаты", url=url)]
    ])