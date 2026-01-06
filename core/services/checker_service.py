from aiogram import Bot
from redis.asyncio import Redis
from config import config

redis = Redis.from_url(config.REDIS_URL)

async def is_user_subscribed(bot: Bot, channel_id: int, user_id: int) -> bool:
    """
    Проверяет подписку с кешированием на 5 минут.
    Защищает от ошибки 429 Too Many Requests.
    """
    cache_key = f"sub_status:{channel_id}:{user_id}"
    
    # 1. Пробуем достать из кеша
    cached = await redis.get(cache_key)
    if cached:
        return cached.decode() == "1"

    # 2. Если нет в кеше — спрашиваем Telegram
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        if member.status in ('creator', 'administrator', 'member', 'restricted'):
            # Запоминаем "Подписан" на 5 минут
            await redis.set(cache_key, "1", ex=300)
            return True
        else:
            # Запоминаем "Не подписан" на 1 минуту (меньше, чтобы быстрее обновить если подпишется)
            await redis.set(cache_key, "0", ex=60)
            return False
    except Exception:
        # Если ошибка (бот не админ или бан API) - считаем что не подписан, не кешируем ошибку надолго
        return False