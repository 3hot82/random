import logging
from aiogram import Bot
from redis.asyncio import Redis
from config import config

# Подключаемся к Redis
redis = Redis.from_url(config.REDIS_URL)
logger = logging.getLogger(__name__)

async def is_user_subscribed(bot: Bot, channel_id: int, user_id: int, force_check: bool = False) -> bool:
    """
    Проверяет подписку пользователя на канал.
    :param force_check: Если True, игнорирует кеш и делает запрос к Telegram.
    """
    cache_key = f"sub_status:{channel_id}:{user_id}"
    
    # 1. Если НЕ принудительная проверка, пробуем достать из кеша
    if not force_check:
        cached_status = await redis.get(cache_key)
        if cached_status is not None:
            return cached_status.decode() == "1"

    # 2. Спрашиваем у Telegram
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        
        # Статусы, которые считаются "подписан"
        if member.status in ('creator', 'administrator', 'member', 'restricted'):
            # Кешируем положительный результат на 5 минут
            await redis.set(cache_key, "1", ex=300)
            return True
        else:
            # Кешируем отрицательный результат на 30 секунд
            await redis.set(cache_key, "0", ex=30)
            return False
            
    except Exception as e:
        # Логируем ошибку, чтобы видеть в консоли, если бот не админ
        logger.error(f"Check sub error (User: {user_id}, Channel: {channel_id}): {e}")
        return False