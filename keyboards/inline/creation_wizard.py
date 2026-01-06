from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models.channel import Channel

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все верно, создать!", callback_data="wizard_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel")]
    ])

# --- НОВОЕ ---
def select_channel_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопки с названиями каналов
    for ch in channels:
        builder.button(text=f"📢 {ch.title}", callback_data=f"select_ch_{ch.channel_id}")
    
    # Кнопка ручного ввода (если канала нет в списке)
    builder.button(text="➕ Другой канал (переслать пост)", callback_data="manual_channel_input")
    
    builder.adjust(1)
    return builder.as_markup()