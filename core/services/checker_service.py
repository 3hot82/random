import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
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
        try:
            cached_status = await redis.get(cache_key)
            if cached_status is not None:
                return cached_status.decode() == "1"
        except Exception as e:
            logger.warning(f"Redis cache error for {cache_key}: {e}")
            # Если кеш недоступен, продолжаем с запросом к Telegram

    # 2. Спрашиваем у Telegram
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        
        # Статусы, которые считаются "подписан"
        if member.status in ('creator', 'administrator', 'member', 'restricted'):
            # Кешируем положительный результат на 5 минут
            await safe_set_cache(cache_key, "1", 300)
            return True
        else:
            # Кешируем отрицательный результат на 30 секунд
            await safe_set_cache(cache_key, "0", 30)
            return False
            
    except TelegramForbiddenError:
        # Бот не имеет прав доступа к каналу
        logger.error(f"Bot has no access to channel {channel_id} (User: {user_id})")
        # Кешируем отрицательный результат на короткое время, так как статус может измениться
        await safe_set_cache(cache_key, "0", 60)
        return False
        
    except TelegramBadRequest as e:
        # Некорректный запрос (например, неверный ID пользователя или канала)
        if "user not found" in str(e).lower() or "chat not found" in str(e).lower():
            logger.warning(f"User or channel not found (User: {user_id}, Channel: {channel_id})")
            # Кешируем отрицательный результат на короткое время
            await safe_set_cache(cache_key, "0", 60)
            return False
        else:
            # Другая ошибка BadRequest
            logger.error(f"Bad request when checking subscription (User: {user_id}, Channel: {channel_id}): {e}")
            return False
            
    except Exception as e:
        # Логируем ошибку, чтобы видеть в консоли, если бот не админ
        logger.error(f"Check sub error (User: {user_id}, Channel: {channel_id}): {e}")
        return False

async def safe_set_cache(key: str, value: str, ex: int):
    """
    Безопасное сохранение в кеш с обработкой ошибок
    """
    try:
        await redis.setex(key, ex, value)
    except Exception as e:
        logger.warning(f"Redis set error for {key}: {e}")