from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import math

from services.premium_service import PremiumService, AnalyticsService
from database.requests.giveaway_repo import get_giveaways_by_owner, count_giveaways_by_owner
from keyboards.inline.dashboard import analytics_kb, giveaway_analytics_kb
from database.models.conversion_funnels import ConversionFunnel, GiveawayHistory, ChannelAnalytics

router = Router()


async def ensure_analytics_records_exist(session: AsyncSession, giveaway_id: int):
    """
    Убедиться, что записи для аналитики существуют для розыгрыша
    """
    # Проверяем, существует ли воронка конверсии для розыгрыша
    conversion_funnel = await session.get(ConversionFunnel, giveaway_id)
    if not conversion_funnel:
        # Создаем новую воронку конверсии
        conversion_funnel = ConversionFunnel(giveaway_id=giveaway_id)
        session.add(conversion_funnel)
        await session.commit()


@router.callback_query(F.data == "show_analytics")
async def show_analytics_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Показать меню аналитики с проверкой премиум-статуса
    """
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь администратором
    from filters.admin_filter import IsAdmin
    is_admin = await IsAdmin().__call__(callback)
    
    if not is_admin:
        # Проверяем статус подписки пользователя
        subscription_status = await PremiumService.get_user_subscription_status(session, user_id)
        
        # Если пользователь не имеет премиум-доступа, запрещаем использование аналитики
        if not subscription_status["is_premium"]:
            return await callback.answer("🔒 PRO аналитика доступна только премиум-пользователям! Обновите тариф.", show_alert=True)
    
    # Получаем статистику по розыгрышам пользователя
    total_giveaways = await count_giveaways_by_owner(session, user_id)
    
    # Формируем сообщение с общей аналитикой
    analytics_text = f"""📈 <b>PRO Аналитика</b>

<b>📊 Общая статистика:</b>
• Создано розыгрышей: {total_giveaways}

<b>🎯 Доступные функции:</b>
• Детальная аналитика по каждому розыгрышу
• Статистика по каналам-спонсорам
• Конверсия участников
• Воронка привлечения

Нажмите на интересующий раздел для просмотра деталей."""
    
    await callback.message.edit_text(
        analytics_text,
        reply_markup=analytics_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_giveaway_analytics:"))
async def view_giveaway_analytics(callback: CallbackQuery, session: AsyncSession):
    """
    Просмотр аналитики по конкретному розыгрышу
    """
    user_id = callback.from_user.id
    giveaway_id = int(callback.data.split(":")[1])
    
    # Проверяем, является ли пользователь администратором
    from filters.admin_filter import IsAdmin
    is_admin = await IsAdmin().__call__(callback)
    
    if not is_admin:
        # Проверяем статус подписки пользователя
        subscription_status = await PremiumService.get_user_subscription_status(session, user_id)
        
        # Если пользователь не имеет премиум-доступа, запрещаем использование аналитики
        if not subscription_status["is_premium"]:
            return await callback.answer("🔒 PRO аналитика доступна только премиум-пользователям! Обновите тариф.", show_alert=True)
    
    # Проверяем, принадлежит ли розыгрыш пользователю
    from database.requests.giveaway_repo import get_giveaway_by_id
    giveaway = await get_giveaway_by_id(session, giveaway_id)
    
    if not giveaway or giveaway.owner_id != user_id:
        return await callback.answer("❌ У вас нет доступа к аналитике этого розыгрыша.", show_alert=True)
    
    # Получаем данные аналитики для розыгрыша
    conversion_funnel = await session.get(ConversionFunnel, giveaway_id)
    giveaway_history = await session.get(GiveawayHistory, giveaway_id)
    
    # Формируем сообщение с детализированной аналитикой
    analytics_parts = [f"📊 <b>ДЕТАЛЬНАЯ АНАЛИТИКА РОЗЫГРЫША #{giveaway_id}</b>\n"]
    
    # Добавляем информацию о розыгрыше
    status_emoji = "🟢" if giveaway.status == "active" else "🟡" if giveaway.status == "finished" else "🔴"
    analytics_parts.append(f"<b>ℹ️ Основная информация:</b>")
    analytics_parts.append(f"• Приз: {giveaway.prize_text[:50]}{'...' if len(giveaway.prize_text) > 50 else ''}")
    analytics_parts.append(f"• Статус: {status_emoji} {giveaway.status.capitalize()}")
    analytics_parts.append(f"• Победителей: {giveaway.winners_count}")
    analytics_parts.append(f"• Дата завершения: {giveaway.finish_time.strftime('%d.%m.%Y %H:%M')}")
    analytics_parts.append("")
    
    # Добавляем информацию о воронке конверсии, если она есть
    if conversion_funnel:
        analytics_parts.append("<b>📈 ВОРОНКА КОНВЕРСИИ:</b>")
        
        # Рассчитываем конверсию
        views = conversion_funnel.post_views
        clicks = conversion_funnel.unique_clicks
        started = conversion_funnel.started_join
        subscribed = conversion_funnel.subscribed_all_required
        participated = conversion_funnel.fully_participated
        
        # Рассчитываем проценты
        click_rate = (clicks / views * 100) if views > 0 else 0
        start_rate = (started / clicks * 100) if clicks > 0 else 0
        sub_rate = (subscribed / started * 100) if started > 0 else 0
        participation_rate = (participated / started * 100) if started > 0 else 0
        
        funnel_stats = [
            f"• Просмотры поста: <b>{views:,}</b>",
            f"• Переходы по кнопке: <b>{clicks:,}</b> (<b>{click_rate:.1f}%</b>)",
            f"• Начали участвовать: <b>{started:,}</b> (<b>{start_rate:.1f}%</b>)",
            f"• Подписались на каналы: <b>{subscribed:,}</b> (<b>{sub_rate:.1f}%</b>)",
            f"• Полностью участвовали: <b>{participated:,}</b> (<b>{participation_rate:.1f}%</b>)",
        ]
        
        if conversion_funnel.completed_captcha > 0:
            captcha_rate = (conversion_funnel.completed_captcha / started * 100) if started > 0 else 0
            funnel_stats.append(f"• Прошли капчу: <b>{conversion_funnel.completed_captcha:,}</b> (<b>{captcha_rate:.1f}%</b>)")
        
        if conversion_funnel.invited_referrals > 0:
            funnel_stats.append(f"• Пригласили друзей: <b>{conversion_funnel.invited_referrals:,}</b>")
        
        analytics_parts.extend(funnel_stats)
        analytics_parts.append("")
    
    # Добавляем информацию из истории розыгрыша, если она есть
    if giveaway_history:
        analytics_parts.append("<b>📋 СТАТИСТИКА РОЗЫГРЫША:</b>")
        
        # Рассчитываем дополнительные метрики
        participants = giveaway_history.total_participants
        new_subs = giveaway_history.new_subscribers
        avg_tickets = giveaway_history.avg_tickets_per_user
        referral_conv = giveaway_history.referral_conversion
        
        if participants > 0:
            sub_rate = (new_subs / participants * 100) if participants > 0 else 0
            analytics_parts.extend([
                f"• Всего участников: <b>{participants:,}</b>",
                f"• Новые подписчики: <b>{new_subs:,}</b> (<b>{sub_rate:.1f}%</b>)",
                f"• Среднее кол-во билетов на участника: <b>{avg_tickets:.2f}</b>",
                f"• Конверсия рефералов: <b>{referral_conv:.2%}</b>",
            ])
            
            if giveaway_history.still_subscribed_after_7d is not None:
                retention_7d_rate = (giveaway_history.still_subscribed_after_7d / new_subs * 100) if new_subs > 0 else 0
                analytics_parts.append(f"• Удержание 7 дней: <b>{giveaway_history.still_subscribed_after_7d}</b> (<b>{retention_7d_rate:.1f}%</b>)")
            
            if giveaway_history.still_subscribed_after_30d is not None:
                retention_30d_rate = (giveaway_history.still_subscribed_after_30d / new_subs * 100) if new_subs > 0 else 0
                analytics_parts.append(f"• Удержание 30 дней: <b>{giveaway_history.still_subscribed_after_30d}</b> (<b>{retention_30d_rate:.1f}%</b>)")
        else:
            analytics_parts.append("• Участников: <b>0</b>")
        
        analytics_parts.append("")
    
    # Добавляем информацию о спонсорах, если есть
    from database.requests.giveaway_repo import get_required_channels
    sponsors = await get_required_channels(session, giveaway_id)
    if sponsors:
        analytics_parts.append(f"<b>🤝 КАНАЛЫ-СПОНСОРЫ ({len(sponsors)}):</b>")
        for sponsor in sponsors[:5]:  # Показываем первые 5 спонсоров
            analytics_parts.append(f"• {sponsor.channel_title}")
        if len(sponsors) > 5:
            analytics_parts.append(f"• ... и ещё {len(sponsors) - 5}")
        analytics_parts.append("")
    
    if not conversion_funnel and not giveaway_history:
        analytics_parts.append("ℹ️ Аналитические данные по этому розыгрышу пока отсутствуют.")
        analytics_parts.append("🔄 Данные будут обновляться в процессе проведения розыгрыша.")
    
    analytics_text = "\n".join(analytics_parts)
    
    await callback.message.edit_text(
        analytics_text,
        reply_markup=giveaway_analytics_kb(giveaway_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("list_giveaways_analytics:"))
async def list_giveaways_analytics(callback: CallbackQuery, session: AsyncSession):
    """
    Показать список розыгрышей для просмотра аналитики
    """
    user_id = callback.from_user.id
    page = int(callback.data.split(":")[1]) if ":" in callback.data else 0
    
    # Проверяем, является ли пользователь администратором
    from filters.admin_filter import IsAdmin
    is_admin = await IsAdmin().__call__(callback)
    
    if not is_admin:
        # Проверяем статус подписки пользователя
        subscription_status = await PremiumService.get_user_subscription_status(session, user_id)
        
        # Если пользователь не имеет премиум-доступа, запрещаем использование аналитики
        if not subscription_status["is_premium"]:
            return await callback.answer("🔒 PRO аналитика доступна только премиум-пользователям! Обновите тариф.", show_alert=True)
    
    # Получаем розыгрыши пользователя с пагинацией
    limit = 10
    offset = page * limit
    giveaways = await get_giveaways_by_owner(session, user_id, limit=limit, offset=offset)
    total_count = await count_giveaways_by_owner(session, user_id)
    total_pages = math.ceil(total_count / limit)
    
    if not giveaways:
        await callback.message.edit_text(
            "📋 У вас пока нет розыгрышей для анализа.",
            reply_markup=analytics_kb()
        )
        await callback.answer()
        return
    
    # Формируем список розыгрышей с краткой аналитикой
    giveaways_list = ["📊 <b>Ваши розыгрыши (для аналитики):</b>\n"]
    
    for gw in giveaways:
        status_emoji = "🟢" if gw.status == "active" else "🟡" if gw.status == "finished" else "🔴"
        giveaways_list.append(f"{status_emoji} <code>#{gw.id}</code> {gw.prize_text[:50]}{'...' if len(gw.prize_text) > 50 else ''}")
    
    # Добавляем навигацию по страницам
    navigation = []
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(f"◀ {(page)}")
        nav_buttons.append(f"{page + 1}/{total_pages}")
        if page < total_pages - 1:
            nav_buttons.append(f"{(page + 2)} ▶")
        navigation.append(" ".join(nav_buttons))
    
    giveaways_list.extend(navigation)
    
    giveaways_text = "\n".join(giveaways_list)
    
    # Создаем клавиатуру со списком розыгрышей
    from keyboards.inline.dashboard import giveaways_list_analytics_kb
    keyboard = giveaways_list_analytics_kb(giveaways, page, total_pages)
    
    await callback.message.edit_text(
        giveaways_text,
        reply_markup=keyboard
    )
    await callback.answer()