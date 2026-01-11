from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.admin.admin_router import admin_router
from keyboards.admin_stats_keyboards import (
    get_stats_menu_keyboard,
    get_back_to_stats_menu_keyboard,
    get_stats_filter_keyboard
)
from services.admin_statistics_service import CachedStatisticsService
from utils.admin_logger import log_admin_action


@admin_router.callback_query(F.data == "admin_stats")
async def show_stats_menu(callback: CallbackQuery):
    keyboard = get_stats_menu_keyboard()
    await callback.message.edit_text("📊 Меню статистики", reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_general_stats")
async def show_general_stats(callback: CallbackQuery, session: AsyncSession):
    service = CachedStatisticsService(session)
    stats = await service.get_general_stats()
    
    message_text = f"""
📊 Общая статистика:
👥 Всего пользователей: {stats['total_users']}
🎁 Активных розыгрышей: {stats['active_giveaways']}
🎫 Всего участий: {stats['total_participations']}
🤖 Потенциальных ботов: {stats['potential_bots']}
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_user_growth")
async def show_user_growth_stats(callback: CallbackQuery, session: AsyncSession):
    service = CachedStatisticsService(session)
    stats = await service.get_user_growth_stats()
    
    message_text = f"""
📈 Рост пользователей:
Сегодня: {stats['new_today']}
За неделю: {stats['new_week']}
За месяц: {stats['new_month']}
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


# Обработчики для временных фильтров
@admin_router.callback_query(F.data.startswith("admin_general_stats_"))
async def show_general_stats_filtered(callback: CallbackQuery, session: AsyncSession):
    # Получаем временной период из callback_data
    period = callback.data.split("_")[-1]
    
    service = CachedStatisticsService(session)
    # В реальной реализации здесь должны быть методы для получения статистики за определенный период
    stats = await service.get_general_stats()
    
    message_text = f"""
📊 Общая статистика ({period}):
👥 Всего пользователей: {stats['total_users']}
🎁 Активных розыгрышей: {stats['active_giveaways']}
🎫 Всего участий: {stats['total_participations']}
🤖 Потенциальных ботов: {stats['potential_bots']}
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


# Заглушка для остальных видов статистики
@admin_router.callback_query(F.data == "admin_premium_stats")
async def show_premium_stats(callback: CallbackQuery, session: AsyncSession):
    # В реальной реализации должен быть метод для получения премиум статистики
    message_text = """
⭐ Премиум статистика:
В разработке...
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_giveaway_stats")
async def show_giveaway_stats(callback: CallbackQuery, session: AsyncSession):
    # В реальной реализации должен быть метод для получения статистики розыгрышей
    message_text = """
🎮 Статистика розыгрышей:
В разработке...
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == "admin_participation_stats")
async def show_participation_stats(callback: CallbackQuery, session: AsyncSession):
    # В реальной реализации должен быть метод для получения статистики участий
    message_text = """
🎯 Статистика участий:
В разработке...
    """.strip()
    
    keyboard = get_back_to_stats_menu_keyboard()
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


# ИСПРАВЛЕНИЕ: Добавлен фильтр .contains("stats"), чтобы не перехватывать другие админские кнопки
@admin_router.callback_query(F.data.startswith("admin_") & F.data.contains("stats"))
async def log_admin_stats_actions(callback: CallbackQuery, session: AsyncSession):
    # Логируем действия только для статистики
    await log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action=f"view_{callback.data.replace('admin_', '')}",
        details={"message_id": callback.message_id}
    )
    # Важно: здесь нет callback.answer(), так как предполагается, что это действие 
    # может быть "прозрачным" или обработано выше, но так как это последний хендлер 
    # в цепочке статистики, то он сработает только если ничего выше не сработало, 
    # но подошло по фильтру. В данном случае это безопасно.