from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from filters.is_admin import IsAdmin
from database.models.user import User
from database.models.giveaway import Giveaway
from keyboards.builders import simple_menu 

router = Router()

@router.message(IsAdmin(), Command("admin"))
async def admin_dashboard(message: types.Message, session: AsyncSession):
    # Сбор статистики
    total_users = await session.scalar(select(func.count(User.user_id)))
    premium_users = await session.scalar(select(func.count(User.user_id)).where(User.is_premium == True))
    active_gws = await session.scalar(select(func.count(Giveaway.id)).where(Giveaway.status == "active"))
    finished_gws = await session.scalar(select(func.count(Giveaway.id)).where(Giveaway.status == "finished"))

    text = (
        f"👑 <b>Панель Администратора</b>\n\n"
        f"👥 <b>Пользователи:</b> {total_users}\n"
        f"🌟 <b>Premium:</b> {premium_users}\n"
        f"🎰 <b>Розыгрыши:</b>\n"
        f" • Активные: {active_gws}\n"
        f" • Завершенные: {finished_gws}\n\n"
        f"Выберите действие:"
    )
    
    # Билдер кнопок (нужно добавить эти callback'и в обработчики)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="👤 Найти юзера", callback_data="admin_find_user")
    kb.button(text="📋 Список активных GW", callback_data="admin_list_active")
    kb.adjust(2, 1)

    await message.answer(text, reply_markup=kb.as_markup())