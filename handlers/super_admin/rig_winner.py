# handlers/super_admin/rig_winner.py
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.callback_data import AdminAction
from database.requests.giveaway_repo import set_predetermined_winner

router = Router()

class RigState(StatesGroup):
    waiting_for_id = State()

@router.callback_query(AdminAction.filter(F.action == "rig"))
async def start_rigging(call: types.CallbackQuery, callback_data: AdminAction, state: FSMContext):
    await state.update_data(gw_id=callback_data.id)
    await state.set_state(RigState.waiting_for_id)
    await call.message.answer(
        f"🕵️‍♂️ <b>Режим бога</b> (Розыгрыш #{callback_data.id})\n"
        f"Пришлите ID пользователя, который ДОЛЖЕН победить.\n"
        f"⚠️ Пользователь обязан нажать кнопку участия, иначе это не сработает!"
    )
    await call.answer()

@router.message(RigState.waiting_for_id)
async def set_winner_id(message: types.Message, state: FSMContext, session: AsyncSession):
    # Добавляем логирование для отладки
    import logging
    logger = logging.getLogger("debug_fsm")
    logger.info(f"DEBUG FSM: User {message.from_user.id} sent message '{message.text}' in state RigState.waiting_for_id")
    
    # Проверяем, не является ли сообщение командой
    if message.text and message.text.startswith('/'):
        await state.clear()
        logger.info(f"DEBUG FSM: User {message.from_user.id} sent command, state cleared")
        return  # Просто игнорируем команду и очищаем состояние
    
    # Проверяем, является ли пользователь администратором
    from filters.is_admin import IsAdmin
    is_admin_filter = IsAdmin()
    if not await is_admin_filter(message):
        await state.clear()
        await message.answer("❌ У вас нет прав для выполнения этой операции.")
        logger.info(f"DEBUG FSM: User {message.from_user.id} is not admin, state cleared")
        return
        
    try:
        winner_id = int(message.text)
    except ValueError:
        logger.info(f"DEBUG FSM: User {message.from_user.id} sent non-numeric input: {message.text}")
        return await message.answer("❌ Нужен числовой ID.")
    
    data = await state.get_data()
    gw_id = data['gw_id']
    
    # Устанавливаем "жучка" в БД
    await set_predetermined_winner(session, gw_id, winner_id)
    
    await message.answer(f"✅ <b>Готово!</b>\nПользователь `{winner_id}` победит в розыгрыше #{gw_id} (если будет участвовать).")
    await state.clear()