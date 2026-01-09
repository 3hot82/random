# Обновленный обработчик статистики с поддержкой дерева кнопок
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone

from filters.is_super_admin import IsSuperAdmin
from database.models.user import User
from database.models.giveaway import Giveaway
from database.models.participant import Participant
from keyboards.callback_data import StatsAction
from keyboards.admin_keyboards import AdminKeyboardFactory

router = Router()


async def get_general_stats(session: AsyncSession):
    """Получение общей статистики"""
    total_users = await session.scalar(select(func.count(User.user_id)))
    premium_users = await session.scalar(
        select(func.count(User.user_id)).where(User.is_premium == True)
    )
    active_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "active")
    )
    finished_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "finished")
    )
    total_participations = await session.scalar(select(func.count()).select_from(Participant))
    
    avg_participants = 0
    # Преобразуем результаты в целые числа, чтобы избежать ошибок с Mock объектами
    active_gws_int = int(active_gws) if active_gws is not None else 0
    finished_gws_int = int(finished_gws) if finished_gws is not None else 0
    
    if active_gws_int + finished_gws_int > 0:
        avg_participants = round(total_participations / (active_gws_int + finished_gws_int), 2)
    
    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "active_gws": active_gws,
        "finished_gws": finished_gws,
        "total_participations": total_participations,
        "avg_participants": avg_participants
    }


async def get_growth_stats(session: AsyncSession):
    """Получение статистики роста пользователей"""
    # Используем настоящее время для корректной работы с часовыми поясами
    now = datetime.now(timezone.utc)
    today_start = (now - timedelta(hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)).replace(tzinfo=None)
    week_ago = (now - timedelta(days=7)).replace(tzinfo=None)
    month_ago = (now - timedelta(days=30)).replace(tzinfo=None)
    
    today_new = await session.scalar(
        select(func.count(User.user_id)).where(User.created_at >= today_start)
    )
    
    week_new = await session.scalar(
        select(func.count(User.user_id)).where(User.created_at >= week_ago)
    )
    
    month_new = await session.scalar(
        select(func.count(User.user_id)).where(User.created_at >= month_ago)
    )
    
    return {
        "today": today_new or 0,
        "week": week_new or 0,
        "month": month_new or 0
    }


async def get_premium_stats(session: AsyncSession):
    """Получение премиум статистики"""
    total_users = await session.scalar(select(func.count(User.user_id)))
    premium_users = await session.scalar(
        select(func.count(User.user_id)).where(User.is_premium == True)
    )
    
    conversion = 0
    total_users_int = int(total_users) if total_users is not None else 0
    premium_users_int = int(premium_users) if premium_users is not None else 0
    
    if total_users_int > 0:
        conversion = round((premium_users_int / total_users_int) * 100, 2)
    
    return {
        "total": total_users,
        "premium": premium_users,
        "conversion": conversion
    }


async def get_giveaways_stats(session: AsyncSession):
    """Получение статистики розыгрышей"""
    active_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "active")
    )
    finished_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "finished")
    )
    total_participations = await session.scalar(select(func.count()).select_from(Participant))
    
    avg_participants = 0
    active_gws_int = int(active_gws) if active_gws is not None else 0
    finished_gws_int = int(finished_gws) if finished_gws is not None else 0
    
    if active_gws_int + finished_gws_int > 0:
        avg_participants = round(total_participations / (active_gws_int + finished_gws_int), 2)
    
    return {
        "active": active_gws,
        "finished": finished_gws,
        "avg_participants": avg_participants,
        "total_participations": total_participations
    }


async def get_participations_stats(session: AsyncSession):
    """Получение статистики участий"""
    total_participations = await session.scalar(select(func.count()).select_from(Participant))
    active_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "active")
    )
    finished_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "finished")
    )
    
    avg_participants = 0
    active_gws_int = int(active_gws) if active_gws is not None else 0
    finished_gws_int = int(finished_gws) if finished_gws is not None else 0
    
    if active_gws_int + finished_gws_int > 0:
        avg_participants = round(total_participations / (active_gws_int + finished_gws_int), 2)
    
    return {
        "total": total_participations,
        "avg_per_giveaway": avg_participants
    }


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "main"))
async def show_stats_main(call: CallbackQuery, session: AsyncSession):
    """Показать главное меню статистики"""
    stats = await get_general_stats(session)
    
    stats_text = (
        f"📊 <b>Общая статистика</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f" • Всего: {stats['total_users']}\n"
        f" • Премиум: {stats['premium_users']}\n\n"
        
        f"🎮 <b>Розыгрыши:</b>\n"
        f" • Активные: {stats['active_gws']}\n"
        f" • Завершенные: {stats['finished_gws']}\n\n"
        
        f"🎯 <b>Участия:</b>\n"
        f" • Всего: {stats['total_participations']}\n"
        f" • Среднее/розыгрыш: {stats['avg_participants']}\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "growth"))
async def show_stats_growth(call: CallbackQuery, session: AsyncSession):
    """Показать статистику роста пользователей"""
    growth = await get_growth_stats(session)
    
    stats_text = (
        f"📈 <b>Статистика роста пользователей</b>\n\n"
        f"👥 <b>Новые пользователи:</b>\n"
        f" • За сегодня: {growth['today']}\n"
        f" • За неделю: {growth['week']}\n"
        f" • За месяц: {growth['month']}\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "premium"))
async def show_stats_premium(call: CallbackQuery, session: AsyncSession):
    """Показать премиум статистику"""
    premium = await get_premium_stats(session)
    
    stats_text = (
        f"⭐ <b>Премиум статистика</b>\n\n"
        f"📊 <b>Общие показатели:</b>\n"
        f" • Всего пользователей: {premium['total']}\n"
        f" • Премиум-подписчики: {premium['premium']}\n"
        f" • Конверсия: {premium['conversion']}%\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "giveaways"))
async def show_stats_giveaways(call: CallbackQuery, session: AsyncSession):
    """Показать статистику розыгрышей"""
    giveaways = await get_giveaways_stats(session)
    
    stats_text = (
        f"🎮 <b>Статистика розыгрышей</b>\n\n"
        f"📊 <b>Розыгрыши:</b>\n"
        f" • Активные: {giveaways['active']}\n"
        f" • Завершенные: {giveaways['finished']}\n\n"
        f"🎯 <b>Участники:</b>\n"
        f" • Всего участий: {giveaways['total_participations']}\n"
        f" • Среднее на розыгрыш: {giveaways['avg_participants']}\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "participations"))
async def show_stats_participations(call: CallbackQuery, session: AsyncSession):
    """Показать статистику участий"""
    participations = await get_participations_stats(session)
    
    stats_text = (
        f"🎯 <b>Статистика участий</b>\n\n"
        f"🎫 <b>Участия:</b>\n"
        f" • Общее количество: {participations['total']}\n"
        f" • Среднее на розыгрыш: {participations['avg_per_giveaway']}\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "refresh"))
async def refresh_stats(call: CallbackQuery, session: AsyncSession):
    """Обновить статистику"""
    stats = await get_general_stats(session)
    
    stats_text = (
        f"📊 <b>Обновленная статистика</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f" • Всего: {stats['total_users']}\n"
        f" • Премиум: {stats['premium_users']}\n\n"
        
        f"🎮 <b>Розыгрыши:</b>\n"
        f" • Активные: {stats['active_gws']}\n"
        f" • Завершенные: {stats['finished_gws']}\n\n"
        
        f"🎯 <b>Участия:</b>\n"
        f" • Всего: {stats['total_participations']}\n"
        f" • Среднее/розыгрыш: {stats['avg_participants']}\n"
    )
    
    try:
        await call.message.edit_text(stats_text, reply_markup=AdminKeyboardFactory.create_stats_menu())
        await call.answer("📊 Статистика обновлена!", show_alert=False)
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise


# Обработчики для подпунктов статистики (детальные просмотры)
@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "growth_today"))
async def show_growth_today(call: CallbackQuery, session: AsyncSession):
    """Показать детальную статистику за сегодня"""
    growth = await get_growth_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"👥 Новые за сегодня: {growth['today']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "growth_week"))
async def show_growth_week(call: CallbackQuery, session: AsyncSession):
    """Показать детальную статистику за неделю"""
    growth = await get_growth_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"📅 Новые за неделю: {growth['week']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "growth_month"))
async def show_growth_month(call: CallbackQuery, session: AsyncSession):
    """Показать детальную статистику за месяц"""
    growth = await get_growth_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"📆 Новые за месяц: {growth['month']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "premium_overview"))
async def show_premium_overview(call: CallbackQuery, session: AsyncSession):
    """Показать общую премиум статистику"""
    premium = await get_premium_stats(session)
    text = f"📊 Премиум статистика:\nВсего: {premium['total']}\nПремиум: {premium['premium']}\nКонверсия: {premium['conversion']}%"
    await call.answer(text, show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "premium_conversion"))
async def show_premium_conversion(call: CallbackQuery, session: AsyncSession):
    """Показать конверсию премиума"""
    premium = await get_premium_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"💰 Конверсия в премиум: {premium['conversion']}%", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "premium_growth"))
async def show_premium_growth(call: CallbackQuery, session: AsyncSession):
    """Показать рост премиума"""
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer("📈 Рост премиум-подписчиков: +12% (пример)", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "giveaways_active"))
async def show_giveaways_active(call: CallbackQuery, session: AsyncSession):
    """Показать активные розыгрыши"""
    giveaways = await get_giveaways_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"🟢 Активные розыгрыши: {giveaways['active']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "giveaways_finished"))
async def show_giveaways_finished(call: CallbackQuery, session: AsyncSession):
    """Показать завершенные розыгрыши"""
    giveaways = await get_giveaways_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"🔴 Завершенные розыгрыши: {giveaways['finished']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "giveaways_avg"))
async def show_giveaways_avg(call: CallbackQuery, session: AsyncSession):
    """Показать среднее количество участников"""
    giveaways = await get_giveaways_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"🎯 Среднее участников: {giveaways['avg_participants']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "participations_total"))
async def show_participations_total(call: CallbackQuery, session: AsyncSession):
    """Показать общее количество участий"""
    participations = await get_participations_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"🎫 Всего участий: {participations['total']}", show_alert=True)


@router.callback_query(IsSuperAdmin(), StatsAction.filter(F.action == "participations_avg"))
async def show_participations_avg(call: CallbackQuery, session: AsyncSession):
    """Показать среднее количество участий на розыгрыш"""
    participations = await get_participations_stats(session)
    # Показываем информацию во всплывающем окне, чтобы избежать редактирования сообщения
    await call.answer(f"📊 Среднее на розыгрыш: {participations['avg_per_giveaway']}", show_alert=True)


# Обработка навигации "Назад" из статистики
@router.callback_query(IsSuperAdmin(), F.data == "admin_menu")
async def navigate_back(call: CallbackQuery, session: AsyncSession):
    """Обработка навигации назад"""
    # Возвращаем в главное меню администратора
    # Используем сессию из data, переданную через middleware
    from sqlalchemy import func, select
    from database.models.user import User
    from database.models.giveaway import Giveaway
    
    # Сбор статистики для главного меню администратора
    total_users = await session.scalar(select(func.count(User.user_id)))
    premium_users = await session.scalar(
        select(func.count(User.user_id)).where(User.is_premium == True)
    )
    active_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "active")
    )
    finished_gws = await session.scalar(
        select(func.count(Giveaway.id)).where(Giveaway.status == "finished")
    )

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
    kb.button(text="👥 Пользователи", callback_data="admin_users")
    kb.button(text="🎮 Розыгрыши", callback_data="admin_giveaways")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="🛡 Безопасность", callback_data="admin_security")
    kb.button(text="⚙️ Настройки", callback_data="admin_settings")
    kb.button(text="📋 Логи", callback_data="admin_logs")
    kb.adjust(2, 2, 2, 1)

    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        # Если сообщение не изменилось, Telegram возвращает ошибку
        # Просто игнорируем эту ошибку и отвечаем пустым ответом
        if "message is not modified" in str(e).lower():
            await call.answer()
        else:
            # Если другая ошибка, пробрасываем дальше
            raise
