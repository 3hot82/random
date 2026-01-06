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
    try:
        winner_id = int(message.text)
    except ValueError:
        return await message.answer("❌ Нужен числовой ID.")

    data = await state.get_data()
    gw_id = data['gw_id']

    # Устанавливаем "жучка" в БД
    await set_predetermined_winner(session, gw_id, winner_id)
    
    await message.answer(f"✅ <b>Готово!</b>\nПользователь `{winner_id}` победит в розыгрыше #{gw_id} (если будет участвовать).")
    await state.clear()