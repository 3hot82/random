import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from database.models.user import User
from database.models.premium_features import UserSubscription, SubscriptionTier
from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.required_channel import GiveawayRequiredChannel
from core.services.checker_service import is_user_subscribed


logger = logging.getLogger(__name__)

# Подключаемся к Redis
redis = Redis.from_url(config.REDIS_URL)


class PremiumCheckerService:
    """
    Сервис для премиум-проверки подписок с использованием кеширования и фоновых задач
    """
    
    def __init__(self):
        self.redis = redis
        
    async def get_user_subscription_status(self, session: AsyncSession, user_id: int) -> Dict:
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
    
    async def get_cached_subscriptions(self, user_id: int) -> Optional[Dict]:
        """
        Получение закешированных подписок пользователя из Redis
        """
        cache_key = f"premium_subs:{user_id}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache get error for {cache_key}: {e}")
        
        return None
    
    async def cache_subscriptions(self, user_id: int, subscriptions: Dict, expire_seconds: int = 300):
        """
        Кеширование подписок пользователя в Redis
        """
        cache_key = f"premium_subs:{user_id}"
        try:
            import json
            await self.redis.setex(cache_key, expire_seconds, json.dumps(subscriptions))
        except Exception as e:
            logger.warning(f"Redis cache set error for {cache_key}: {e}")
    
    async def batch_check_subscriptions(
        self, 
        bot: Bot, 
        user_id: int, 
        giveaway_id: int, 
        session: AsyncSession,
        force_check: bool = False
    ) -> Tuple[bool, List[Dict]]:
        """
        Премиум-проверка всех подписок пользователя на каналы розыгрыша
        """
        # Получаем розыгрыш и каналы
        giveaway = await session.get(Giveaway, giveaway_id)
        if not giveaway:
            return False, []
        
        # Получаем список каналов для проверки
        required_channels = await session.execute(
            select(GiveawayRequiredChannel).where(
                GiveawayRequiredChannel.giveaway_id == giveaway_id
            )
        )
        required_channels = required_channels.scalars().all()
        
        # Добавляем основной канал розыгрыша
        all_channels = [(giveaway.channel_id, "Основной канал")]
        all_channels.extend([(ch.channel_id, ch.channel_title) for ch in required_channels])
        
        # Проверяем наличие премиум-функций у пользователя
        user_subscription = await self.get_user_subscription_status(session, user_id)
        has_premium_check = user_subscription["features"]["has_realtime_subscription_check"]
        
        # Определяем TTL кеша в зависимости от наличия премиум-функций
        cache_ttl = 60 if has_premium_check else 300 # 1 мин для премиум, 5 мин для обычных
        
        # Если есть премиум-проверка, пробуем использовать кеш
        cached_results = None
        if has_premium_check and not force_check:
            cached_results = await self.get_cached_subscriptions(user_id)
        
        if cached_results and not force_check:
            # Проверяем, актуальны ли кешированные данные для этого розыгрыша
            cached_giveaway_id = cached_results.get("giveaway_id")
            if cached_giveaway_id == giveaway_id:
                return cached_results["all_subscribed"], cached_results["channels_status"]
        
        # Выполняем проверку подписок
        channels_status = []
        all_subscribed = True
        
        # Параллельная проверка всех каналов
        tasks = []
        for channel_id, channel_title in all_channels:
            tasks.append(
                self._check_single_subscription(
                    bot, user_id, channel_id, channel_title, force_check
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error checking subscription: {result}")
                all_subscribed = False
                channels_status.append({
                    "title": "Ошибка проверки",
                    "is_subscribed": False,
                    "error": str(result)
                })
            else:
                channels_status.append(result)
                if not result["is_subscribed"]:
                    all_subscribed = False
        
        # Кешируем результаты, если доступна премиум-функция
        if has_premium_check:
            cache_data = {
                "giveaway_id": giveaway_id,
                "all_subscribed": all_subscribed,
                "channels_status": channels_status,
                "checked_at": datetime.utcnow().isoformat()
            }
            await self.cache_subscriptions(user_id, cache_data, cache_ttl)
        
        return all_subscribed, channels_status
    
    async def _check_single_subscription(
        self, 
        bot: Bot, 
        user_id: int, 
        channel_id: int, 
        channel_title: str, 
        force_check: bool
    ) -> Dict:
        """
        Проверка подписки на один канал
        """
        try:
            is_subscribed = await is_user_subscribed(bot, channel_id, user_id, force_check=force_check)
            return {
                "title": channel_title,
                "channel_id": channel_id,
                "is_subscribed": is_subscribed
            }
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} to channel {channel_id}: {e}")
            return {
                "title": channel_title,
                "channel_id": channel_id,
                "is_subscribed": False,
                "error": str(e)
            }
    
    async def validate_and_disqualify_participants(self, bot: Bot, session: AsyncSession):
        """
        Фоновая задача: проверка подписок всех участников активных розыгрышей
        """
        # Получаем все активные розыгрыши
        active_giveaways = await session.execute(
            select(Giveaway).where(Giveaway.status == "active")
        )
        active_giveaways = active_giveaways.scalars().all()
        
        for giveaway in active_giveaways:
            # Получаем всех участников розыгрыша
            participants = await session.execute(
                select(Participant).where(Participant.giveaway_id == giveaway.id)
            )
            participants = participants.scalars().all()
            
            for participant in participants:
                # Проверяем подписки участника
                all_subscribed, _ = await self.batch_check_subscriptions(
                    bot, participant.user_id, giveaway.id, session
                )
                
                if not all_subscribed:
                    # Дисквалифицируем участника
                    await self.disqualify_participant(
                        session, participant.user_id, giveaway.id, bot
                    )
    
    async def disqualify_participant(
        self, 
        session: AsyncSession, 
        user_id: int, 
        giveaway_id: int, 
        bot: Bot
    ):
        """
        Дисквалификация участника из розыгрыша
        """
        try:
            # Удаление участника из розыгрыша
            participant = await session.get(Participant, {"user_id": user_id, "giveaway_id": giveaway_id})
            if participant:
                await session.delete(participant)
                await session.commit()
                
                # Уведомление участника
                try:
                    await bot.send_message(
                        user_id,
                        f"⚠️ Вы были удалены из розыгрыша #{giveaway_id}, "
                        "так как отписались от одного из обязательных каналов."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error disqualifying participant {user_id} from giveaway {giveaway_id}: {e}")
    
    async def track_subscription_changes(self, user_id: int):
        """
        Отслеживание изменений подписки пользователя (инвалидация кеша)
        """
        # Инвалидируем кеш подписок пользователя
        cache_key = f"premium_subs:{user_id}"
        try:
            await self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Redis cache invalidation error for {cache_key}: {e}")
        
        logger.info(f"Subscription cache invalidated for user {user_id}")
