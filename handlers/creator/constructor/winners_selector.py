from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from keyboards.inline.constructor import winners_selector_kb
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.control_message import refresh_constructor_view
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager

router = Router()

@router.callback_query(F.data == "constr_winners_menu")
async def winners_menu(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    # Показываем меню выбора победителей (Превью + Клавиатура победителей)
    await refresh_constructor_view(
        bot, state, call.message.chat.id, 
        hint_key='winners', 
        custom_keyboard=winners_selector_kb()
    )
    await call.answer()

@router.callback_query(F.data.startswith("constr_set_winners:"))
async def set_winners(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    winners_count = int(call.data.split(":")[-1])
    await state.update_data(winners=winners_count)
    
    # Возвращаемся в главное меню (hint_key='publish' или 'default')
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    await call.answer(f"✅ Победителей: {winners_count}")

@router.callback_query(F.data == "constr_set_winners_input")
async def ask_winners_input(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ConstructorState.editing_winners)
    
    # Удаляем интерфейс
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    msg = await call.message.answer("🔢 <b>Введите количество победителей</b> (1-50):")
    manager.add_temp_message(msg)
    await update_message_manager(state, manager)

@router.message(ConstructorState.editing_winners)
async def process_winners_input(message: types.Message, state: FSMContext, bot: Bot):
    try: await message.delete()
    except: pass
    
    manager = await get_message_manager(state)
    text = message.text.strip()
    
    if not text.isdigit() or not (1 <= int(text) <= 50):
        msg = await message.answer("❌ Введите число от 1 до 50")
        manager.add_temp_message(msg)
        await update_message_manager(state, manager)
        return
        
    await state.update_data(winners=int(text))
    await state.set_state(ConstructorState.init)
    
    # Возврат в меню
    await refresh_constructor_view(bot, state, message.chat.id, hint_key='publish')