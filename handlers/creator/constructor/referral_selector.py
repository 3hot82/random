from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from keyboards.inline.constructor import referral_selector_kb
from handlers.creator.constructor.structure import ConstructorState
from handlers.creator.constructor.control_message import refresh_constructor_view
from handlers.creator.constructor.message_manager import get_message_manager, update_message_manager

router = Router()

@router.callback_query(F.data == "constr_ref_menu")
async def ref_menu(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await refresh_constructor_view(
        bot, state, call.message.chat.id, 
        hint_key='referral', 
        custom_keyboard=referral_selector_kb()
    )
    await call.answer()

@router.callback_query(F.data.startswith("constr_set_ref:"))
async def set_ref(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    count = int(call.data.split(":")[-1])
    await state.update_data(ref_req=count)
    
    await refresh_constructor_view(bot, state, call.message.chat.id, hint_key='publish')
    text = "Выкл" if count == 0 else f"{count} друзей"
    await call.answer(f"✅ Реф. система: {text}")

@router.callback_query(F.data == "constr_set_ref_input")
async def ask_ref_input(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ConstructorState.editing_referral)
    
    manager = await get_message_manager(state)
    await manager.delete_all(bot, call.message.chat.id)
    
    msg = await call.message.answer("🔗 <b>Введите количество друзей</b> (0-10):")
    manager.add_temp_message(msg)
    await update_message_manager(state, manager)

@router.message(ConstructorState.editing_referral)
async def process_ref_input(message: types.Message, state: FSMContext, bot: Bot):
    try: await message.delete()
    except: pass
    
    manager = await get_message_manager(state)
    text = message.text.strip()
    
    if not text.isdigit() or not (0 <= int(text) <= 10):
        msg = await message.answer("❌ Введите число от 0 до 10")
        manager.add_temp_message(msg)
        await update_message_manager(state, manager)
        return
        
    await state.update_data(ref_req=int(text))
    await state.set_state(ConstructorState.init)
    
    await refresh_constructor_view(bot, state, message.chat.id, hint_key='publish')