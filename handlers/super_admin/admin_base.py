from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from filters.is_super_admin import IsSuperAdmin
from database.models.user import User
from database.models.giveaway import Giveaway
from keyboards.callback_data import StatsAction, NavigationAction, UsersAction
from keyboards.inline.admin_panel import stats_main_keyboard

router = Router()


@router.message(IsSuperAdmin(), Command("admin"))
async def admin_dashboard(message: Message, session: AsyncSession):
    """Главное меню администратора"""
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

    # Создаем клавиатуру с основными действиями
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data=StatsAction(action="main").pack())
    kb.button(text="👥 Пользователи", callback_data=UsersAction(action="main").pack())
    kb.button(text="🎮 Розыгрыши", callback_data="admin_giveaways")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="🛡 Безопасность", callback_data="admin_security")
    kb.button(text="⚙️ Настройки", callback_data="admin_settings")
    kb.button(text="📋 Логи", callback_data="admin_logs")
    kb.adjust(2, 2, 2, 1)

    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(IsSuperAdmin(), F.data == "admin_menu")
async def admin_menu_callback(call: CallbackQuery, session: AsyncSession):
    """Обработчик для возврата в главное меню администратора"""
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

    # Создаем клавиатуру с основными действиями
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data=StatsAction(action="main").pack())
    kb.button(text="👥 Пользователи", callback_data=UsersAction(action="main").pack())
    kb.button(text="🎮 Розыгрыши", callback_data="admin_giveaways")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="🛡 Безопасность", callback_data="admin_security")
    kb.button(text="⚙️ Настройки", callback_data="admin_settings")
    kb.button(text="📋 Логи", callback_data="admin_logs")
    kb.adjust(2, 2, 2, 1)

    await call.message.edit_text(text, reply_markup=kb.as_markup())


# Обработка навигации из других разделов
@router.callback_query(IsSuperAdmin(), F.data == "admin_stats")
async def show_stats_from_main(call: CallbackQuery, session: AsyncSession):
    """Переход в статистику из главного меню"""
    from handlers.super_admin.stats_handler import show_stats_main
    await show_stats_main(call, session)