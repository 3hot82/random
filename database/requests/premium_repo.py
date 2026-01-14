from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.dialects.postgresql import insert
from database.models import User, Giveaway, Participant, ConversionFunnel, GiveawayHistory, ChannelAnalytics, SubscriptionTier, UserSubscription, PremiumFeatureUsage


# --- Функции для работы с премиум-подписками ---

async def get_user_subscription_status(session: AsyncSession, user_id: int):
    """
    Получение статуса подписки пользователя
    """
    # Проверяем, есть ли активная подписка у пользователя
    stmt = select(UserSubscription).join(SubscriptionTier).where(
        UserSubscription.user_id == user_id,
        UserSubscription.is_active == True
    ).order_by(UserSubscription.end_date.desc())
    
    result = await session.execute(stmt)
    user_sub = result.scalar_one_or_none()
    
    if not user_sub:
        # Проверяем, является ли пользователь премиум-пользователем через старую систему
        user = await session.get(User, user_id)
        if user and user.is_premium:
            return {
                "is_premium": True,
                "tier_name": "legacy_premium",
                "expires_at": user.premium_until,
                "features": {
                    "max_concurrent_giveaways": 10,
                    "max_sponsor_channels": 20,
                    "has_realtime_subscription_check": True
                }
            }
        return {
            "is_premium": False,
            "tier_name": "free",
            "expires_at": None,
            "features": {
                "max_concurrent_giveaways": 1,
                "max_sponsor_channels": 2,
                "has_realtime_subscription_check": False
            }
        }
    
    # Получаем информацию о тарифе
    tier = await session.get(SubscriptionTier, user_sub.tier_id)
    
    return {
        "is_premium": True,
        "tier_name": tier.name,
        "expires_at": user_sub.end_date,
        "features": {
            "max_concurrent_giveaways": tier.max_concurrent_giveaways_premium if user_sub.is_active else tier.max_concurrent_giveaways,
            "max_sponsor_channels": tier.max_sponsor_channels_premium if user_sub.is_active else tier.max_sponsor_channels,
            "has_realtime_subscription_check": tier.has_realtime_subscription_check and user_sub.is_active
        }
    }


async def create_user_subscription(
    session: AsyncSession, 
    user_id: int, 
    tier_id: int, 
    start_date: datetime = None, 
    end_date: datetime = None,
    auto_renew: bool = False
):
    """
    Создание новой подписки для пользователя
    """
    if start_date is None:
        start_date = datetime.utcnow()
    
    subscription = UserSubscription(
        user_id=user_id,
        tier_id=tier_id,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        auto_renew=auto_renew
    )
    
    session.add(subscription)
    await session.commit()
    
    return subscription


async def deactivate_user_subscription(session: AsyncSession, user_id: int):
    """
    Деактивация подписки пользователя
    """
    stmt = update(UserSubscription).where(
        UserSubscription.user_id == user_id,
        UserSubscription.is_active == True
    ).values(is_active=False)
    
    await session.execute(stmt)
    await session.commit()


# --- Функции для работы с ограничениями тарифов ---

async def get_max_concurrent_giveaways(session: AsyncSession, user_id: int) -> int:
    """
    Получение максимального количества одновременных розыгрышей для пользователя
    """
    subscription_status = await get_user_subscription_status(session, user_id)
    return subscription_status["features"]["max_concurrent_giveaways"]


async def get_max_sponsor_channels(session: AsyncSession, user_id: int) -> int:
    """
    Получение максимального количества каналов-спонсоров для пользователя
    """
    subscription_status = await get_user_subscription_status(session, user_id)
    return subscription_status["features"]["max_sponsor_channels"]


async def can_create_giveaway(session: AsyncSession, user_id: int) -> tuple[bool, str]:
    """
    Проверка возможности создания нового розыгрыша пользователем
    """
    max_concurrent = await get_max_concurrent_giveaways(session, user_id)
    
    # Считаем активные розыгрыши пользователя
    active_count = await session.execute(
        select(Giveaway).where(
            and_(
                Giveaway.owner_id == user_id,
                Giveaway.status.in_(['active'])
            )
        )
    )
    active_count = len(active_count.scalars().all())
    
    if active_count >= max_concurrent:
        return False, f"У вас {active_count} активных розыгрышей. Лимит: {max_concurrent}. Обновите тариф!"
    
    return True, ""


# --- Функции для работы с использованием премиум-функций ---

async def increment_premium_feature_usage(
    session: AsyncSession, 
    user_id: int, 
    feature_name: str
) -> bool:
    """
    Увеличение счетчика использования премиум-функции
    Возвращает True, если использование разрешено, иначе False
    """
    # Получаем или создаем запись о использовании функции
    stmt = select(PremiumFeatureUsage).where(
        PremiumFeatureUsage.user_id == user_id,
        PremiumFeatureUsage.feature_name == feature_name
    )
    result = await session.execute(stmt)
    usage_record = result.scalar_one_or_none()
    
    if not usage_record:
        # Создаем новую запись
        tier_status = await get_user_subscription_status(session, user_id)
        
        # Для простоты, в реальной реализации лимиты будут зависеть от тарифа
        if feature_name == "realtime_subscription_check":
            usage_limit = 1000  # Пример лимита для премиум-проверки
            reset_period = "daily"
        else:
            usage_limit = None  # Безлимитно
            reset_period = None
            
        usage_record = PremiumFeatureUsage(
            user_id=user_id,
            feature_name=feature_name,
            usage_count=1,
            usage_limit=usage_limit,
            reset_period=reset_period
        )
        session.add(usage_record)
        await session.commit()
        return True
    
    # Проверяем лимиты
    if usage_record.usage_limit is not None:
        # Проверяем, нужно ли сбросить счетчик
        now = datetime.utcnow()
        if usage_record.reset_period == "daily" and usage_record.last_reset.date() < now.date():
            usage_record.usage_count = 0
            usage_record.last_reset = now
        elif usage_record.reset_period == "weekly":
            days_since_reset = (now.date() - usage_record.last_reset.date()).days
            if days_since_reset >= 7:
                usage_record.usage_count = 0
                usage_record.last_reset = now
        elif usage_record.reset_period == "monthly":
            if usage_record.last_reset.month != now.month or usage_record.last_reset.year != now.year:
                usage_record.usage_count = 0
                usage_record.last_reset = now
        
        # Проверяем лимит
        if usage_record.usage_count >= usage_record.usage_limit:
            return False
    
    # Увеличиваем счетчик
    usage_record.usage_count += 1
    await session.commit()
    
    return True


# --- Функции для работы с аналитикой ---

async def create_conversion_funnel(session: AsyncSession, giveaway_id: int):
    """
    Создание записи воронки конверсии для розыгрыша
    """
    funnel = ConversionFunnel(giveaway_id=giveaway_id)
    session.add(funnel)
    await session.commit()
    
    return funnel


async def update_conversion_funnel(
    session: AsyncSession,
    giveaway_id: int,
    field: str,
    increment: int = 1
):
    """
    Обновление поля воронки конверсии
    """
    stmt = select(ConversionFunnel).where(ConversionFunnel.giveaway_id == giveaway_id)
    result = await session.execute(stmt)
    funnel = result.scalar_one_or_none()
    
    if not funnel:
        funnel = await create_conversion_funnel(session, giveaway_id)
    
    # Обновляем значение поля
    current_value = getattr(funnel, field, 0)
    setattr(funnel, field, current_value + increment)
    
    await session.commit()


async def create_giveaway_history(session: AsyncSession, giveaway_id: int):
    """
    Создание записи истории розыгрыша
    """
    giveaway = await session.get(Giveaway, giveaway_id)
    if not giveaway:
        return None
    
    # Считаем количество участников
    participants_count = await session.execute(
        select(Participant).where(Participant.giveaway_id == giveaway_id)
    )
    participants_count = len(participants_count.scalars().all())
    
    history = GiveawayHistory(
        giveaway_id=giveaway_id,
        finished_at=giveaway.finish_time,
        total_participants=participants_count,
        unique_participants=participants_count,
        total_tickets=participants_count  # Предполагаем 1 билет на участника
    )
    session.add(history)
    await session.commit()
    
    return history


async def update_channel_analytics(
    session: AsyncSession,
    channel_id: int,
    channel_title: str,
    new_subscriber: bool = False,
    unsubscribe: bool = False
):
    """
    Обновление аналитики канала
    """
    stmt = select(ChannelAnalytics).where(ChannelAnalytics.channel_telegram_id == channel_id)
    result = await session.execute(stmt)
    analytics = result.scalar_one_or_none()
    
    if not analytics:
        analytics = ChannelAnalytics(
            channel_telegram_id=channel_id,
            channel_title=channel_title,
            times_used_as_sponsor=0,
            new_subscribers_brought=0 if not new_subscriber else 1,
            avg_conversion=0.0,
            immediate_unsub_rate=0.0 if not unsubscribe else 1.0,
            retention_7d=0.0,
            retention_30d=0.0,
            engagement_score=0.0,
            failed_checks=0,
            avg_check_time=timedelta(seconds=0),
            rank_by_conversion=0,
            rank_by_retention=0
        )
        session.add(analytics)
    else:
        if new_subscriber:
            analytics.new_subscribers_brought += 1
        if unsubscribe:
            # Здесь потребуется более сложная логика для расчета коэффициента отписок
            pass
    
    await session.commit()