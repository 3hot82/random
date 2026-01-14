from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import (
    get_user_subscription_status,
    create_user_subscription,
    deactivate_user_subscription,
    get_max_concurrent_giveaways,
    get_max_sponsor_channels,
    can_create_giveaway,
    increment_premium_feature_usage,
    create_conversion_funnel,
    update_conversion_funnel,
    create_giveaway_history,
    update_channel_analytics
)


class PremiumService:
    """
    Сервис для работы с премиум-функциями
    """
    
    @staticmethod
    async def get_user_subscription_status(session: AsyncSession, user_id: int) -> Dict:
        """
        Получение статуса подписки пользователя
        """
        return await get_user_subscription_status(session, user_id)
    
    @staticmethod
    async def subscribe_user(
        session: AsyncSession, 
        user_id: int, 
        tier_id: int, 
        start_date: datetime = None, 
        end_date: datetime = None,
        auto_renew: bool = False
    ):
        """
        Подписка пользователя на тариф
        """
        return await create_user_subscription(
            session, user_id, tier_id, start_date, end_date, auto_renew
        )
    
    @staticmethod
    async def unsubscribe_user(session: AsyncSession, user_id: int):
        """
        Отписка пользователя от тарифа
        """
        return await deactivate_user_subscription(session, user_id)
    
    @staticmethod
    async def can_create_giveaway(session: AsyncSession, user_id: int) -> tuple[bool, str]:
        """
        Проверка возможности создания розыгрыша
        """
        return await can_create_giveaway(session, user_id)
    
    @staticmethod
    async def get_max_concurrent_giveaways(session: AsyncSession, user_id: int) -> int:
        """
        Получение максимального количества одновременных розыгрышей
        """
        return await get_max_concurrent_giveaways(session, user_id)
    
    @staticmethod
    async def get_max_sponsor_channels(session: AsyncSession, user_id: int) -> int:
        """
        Получение максимального количества каналов-спонсоров
        """
        return await get_max_sponsor_channels(session, user_id)
    
    @staticmethod
    async def use_premium_feature(session: AsyncSession, user_id: int, feature_name: str) -> bool:
        """
        Использование премиум-функции (с проверкой лимитов)
        """
        return await increment_premium_feature_usage(session, user_id, feature_name)


class AnalyticsService:
    """
    Сервис для работы с аналитикой
    """
    
    @staticmethod
    async def create_conversion_funnel(session: AsyncSession, giveaway_id: int):
        """
        Создание воронки конверсии для розыгрыша
        """
        return await create_conversion_funnel(session, giveaway_id)
    
    @staticmethod
    async def update_conversion_funnel(
        session: AsyncSession,
        giveaway_id: int,
        field: str,
        increment: int = 1
    ):
        """
        Обновление поля воронки конверсии
        """
        return await update_conversion_funnel(session, giveaway_id, field, increment)
    
    @staticmethod
    async def create_giveaway_history(session: AsyncSession, giveaway_id: int):
        """
        Создание истории розыгрыша
        """
        return await create_giveaway_history(session, giveaway_id)
    
    @staticmethod
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
        return await update_channel_analytics(
            session, 
            channel_id, 
            channel_title, 
            new_subscriber, 
            unsubscribe
        )


class LimitChecker:
    """
    Класс для проверки лимитов пользователя
    """
    
    @staticmethod
    async def check_giveaway_creation_limits(session: AsyncSession, user_id: int) -> tuple[bool, str]:
        """
        Проверка лимитов на создание розыгрыша
        """
        can_create, message = await can_create_giveaway(session, user_id)
        return can_create, message
    
    @staticmethod
    async def check_sponsor_channel_limits(
        session: AsyncSession, 
        user_id: int, 
        current_count: int
    ) -> tuple[bool, str]:
        """
        Проверка лимитов на количество каналов-спонсоров
        """
        max_channels = await get_max_sponsor_channels(session, user_id)
        
        if current_count >= max_channels:
            return False, f"Лимит спонсоров: {max_channels}. Текущее: {current_count}"
        
        return True, ""