from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.builder import KeyboardBuilder, ButtonType


def join_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    """Кнопка под постом в канале"""
    url = f"https://t.me/{bot_username}?start=gw_{giveaway_id}"
    return KeyboardBuilder() \
        .add_button("Участвовать 🎁", ButtonType.URL, url=url) \
        .build()


def check_subscription_kb(gw_id: int, channels_status: list) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру со списком каналов.
    channels_status: список словарей {'title': str, 'link': str, 'is_subscribed': bool}
    """
    builder = KeyboardBuilder()
    
    for ch in channels_status:
        if ch['is_subscribed']:
            # Если подписан - ставим галочку
            text = f"✅ {ch['title']}"
        else:
            # Если нет - ставим рупор
            text = f"📢 {ch['title']}"
            
        # Ссылка нужна в любом случае
        builder.add_button(text, ButtonType.URL, url=ch['link'])
    
    # Кнопка проверки
    builder.add_button("🔄 Проверить подписки", ButtonType.CALLBACK, f"check_sub:{gw_id}")
    
    return builder.adjust(1).build()


def results_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start=res_{giveaway_id}"
    return KeyboardBuilder() \
        .add_button("📋 Проверить результаты", ButtonType.URL, url=url) \
        .build()