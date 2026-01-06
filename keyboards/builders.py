# keyboards/builders.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def simple_menu(text: str, callback_data: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder