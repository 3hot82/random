from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

class GiveawayWizard(StatesGroup):
    waiting_for_text = State()
    waiting_for_channel = State()
    waiting_for_sponsors = State() # <--- НОВОЕ СОСТОЯНИЕ
    waiting_for_winners = State()
    waiting_for_time = State()
    confirmation = State()

@router.message(Command("new"))
async def start_wizard(message: types.Message, state: FSMContext):
    await state.set_state(GiveawayWizard.waiting_for_text)
    await message.answer(
        "📝 <b>Создание розыгрыша (Шаг 1/6)</b>\n\n"
        "Пришлите текст поста или фото с описанием приза."
    )