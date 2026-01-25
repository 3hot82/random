from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

class ConstructorState(StatesGroup):
    init = State()
    editing_short_description = State()  # Новое состояние для ввода краткого описания - теперь первым
    editing_content = State()
    confirm_short_text = State()
    adding_channel = State()
    adding_channel_link = State()
    editing_winners = State()  # Новое состояние для ввода победителей вручную
    editing_referral = State() # Новое состояние для ввода рефералов вручную

async def safe_edit_to_text(message: types.Message, text: str, reply_markup=None):
    """
    Безопасно переключает сообщение в текстовый режим.
    """
    try:
        if message.photo or message.video or message.animation or message.document:
            await message.delete()
            await message.answer(text, reply_markup=reply_markup)
        else:
            await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        try: await message.edit_text(text, reply_markup=reply_markup)
        except: pass
    except Exception:
        await message.answer(text, reply_markup=reply_markup)