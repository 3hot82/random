from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def join_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    """Кнопка под постом в канале"""
    url = f"https://t.me/{bot_username}?start=gw_{giveaway_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать 🎁", url=url)]
    ])

def check_subscription_kb(gw_id: int, channels_status: list) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру со списком каналов.
    channels_status: список словарей {'title': str, 'link': str, 'is_subscribed': bool}
    """
    builder = InlineKeyboardBuilder()
    
    for ch in channels_status:
        if ch['is_subscribed']:
            # Если подписан - ставим галочку
            text = f"✅ {ch['title']}"
        else:
            # Если нет - ставим рупор
            text = f"📢 {ch['title']}"
            
        # Ссылка нужна в любом случае
        builder.button(text=text, url=ch['link'])
    
    # Кнопка проверки
    builder.button(text="🔄 Проверить подписки", callback_data=f"check_sub:{gw_id}")
    
    builder.adjust(1)
    return builder.as_markup()

def results_keyboard(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start=res_{giveaway_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Проверить результаты", url=url)]
    ])