from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from database.models.user import User
from filters.is_admin import IsAdmin

router = Router()

class AdminUserState(StatesGroup):
    waiting_for_id_prem = State()

@router.callback_query(IsAdmin(), F.data == "admin_find_user")
async def ask_user_id(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("🆔 Введите ID пользователя для выдачи/снятия Premium:")
    await state.set_state(AdminUserState.waiting_for_id_prem)
    await call.answer()

@router.message(IsAdmin(), AdminUserState.waiting_for_id_prem)
async def toggle_premium(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        target_id = int(message.text)
    except ValueError:
        return await message.answer("❌ Это не число.")

    user = await session.get(User, target_id)
    if not user:
        return await message.answer("❌ Пользователь не найден в базе.")

    # Переключаем статус
    new_status = not user.is_premium
    user.is_premium = new_status
    await session.commit()
    
    status_str = "✅ ВЫДАН" if new_status else "❌ СНЯТ"
    await message.answer(f"Premium для пользователя {target_id} успешно {status_str}.")
    await state.clear()