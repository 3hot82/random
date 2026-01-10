from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from database.models import User, Giveaway, Participant, AdminLog
from typing import Dict, Any


class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_general_stats(self) -> dict:
        """
        Получение общей статистики
        """
        # Всего пользователей
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        
        # Активных розыгрышей
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        
        # Всего участий
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        
        # Пользователей без username (потенциально боты)
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        return {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
    
    async def get_user_growth_stats(self) -> dict:
        """
        Получение статистики роста пользователей
        """
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        new_today = await self.session.scalar(
            select(func.count(User.user_id)).where(
                func.date(User.created_at) == today
            )
        )
        
        new_week = await self.session.scalar(
            select(func.count(User.user_id)).where(
                User.created_at >= week_ago
            )
        )
        
        new_month = await self.session.scalar(
            select(func.count(User.user_id)).where(
                User.created_at >= month_ago
            )
        )
        
        return {
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month
        }


class StatsCache:
    def __init__(self, ttl: int = 300):  # 5 минут
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.ttl = timedelta(seconds=ttl)
    
    def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, datetime.now())


class CachedStatisticsService(StatisticsService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.cache = StatsCache()
    
    async def get_general_stats(self) -> dict:
        cache_key = "general_stats"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Всего пользователей
        total_users = await self.session.scalar(select(func.count(User.user_id)))
        
        # Активных розыгрышей
        active_giveaways = await self.session.scalar(
            select(func.count(Giveaway.id)).where(Giveaway.status == "active")
        )
        
        # Всего участий
        total_participations = await self.session.scalar(
            select(func.count(Participant.user_id))
        )
        
        # Пользователей без username (потенциально боты)
        potential_bots = await self.session.scalar(
            select(func.count(User.user_id)).where(User.username.is_(None))
        )
        
        result = {
            "total_users": total_users,
            "active_giveaways": active_giveaways,
            "total_participations": total_participations,
            "potential_bots": potential_bots
        }
        
        self.cache.set(cache_key, result)
        return result