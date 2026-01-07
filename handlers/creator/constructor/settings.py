from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.user import User
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.control_message import get_control_hint, refresh_constructor_view
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(F.data == "constr_edit_content")
async def ask_new_content(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ConstructorState.editing_content)
    
    # Удаляем текущий интерфейс (превью и кнопки)
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    # Шлем приглашение к вводу "Шаг 1"
    hint_text = await get_control_hint('content')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="constr_back_main")]])
    msg = await call.message.answer(hint_text, reply_markup=kb)
    
    # Запоминаем как инструкцию
    manager.set_instruction_message(msg)
    await update_message_manager(state, manager)

@router.callback_query(F.data.startswith("constr_set_winners:"))
async def set_winners(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    count = int(call.data.split(":")[-1])
    await state.update_data(winners=count)
    # Перерисовываем
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer(f"✅ Победителей: {count}")

@router.callback_query(F.data.startswith("constr_set_ref:"))
async def set_ref(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    count = int(call.data.split(":")[-1])
    await state.update_data(ref_req=count)
    # Перерисовываем
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer(f"✅ Рефералов: {count}")

@router.callback_query(F.data == "constr_toggle_cap")
async def toggle_cap(call: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    
    if not data['is_captcha']:
        user = await session.get(User, call.from_user.id)
        if not user or not user.is_premium:
            return await call.answer("🔒 Функция доступна только с Premium!", show_alert=True)
            
    await state.update_data(is_captcha=not data['is_captcha'])
    # Перерисовываем
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer("✅ Настройка изменена")

@router.callback_query(F.data == "constr_back_main")
async def back_to_main(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ConstructorState.init)
    # Возвращаем интерфейс
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='default')