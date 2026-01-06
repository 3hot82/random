import uuid
from redis.asyncio import Redis
from config import config

# Подключаемся к Redis (используем тот же URL, что в конфиге)
redis = Redis.from_url(config.REDIS_URL)

async def create_ref_link(user_id: int) -> str:
    """
    Создает короткий UUID-токен, который указывает на реальный user_id.
    Токен живет 30 дней.
    """
    # Генерируем уникальный токен (без тире, чтобы был короче)
    token = uuid.uuid4().hex[:12] 
    key = f"ref_map:{token}"
    
    # Проверяем, может у юзера уже есть активный токен (опционально), 
    # но проще генерировать новый или хранить обратный индекс.
    # Для скорости просто пишем:
    await redis.set(key, user_id, ex=2592000) # 30 дней
    return token

async def resolve_ref_link(token: str) -> int | None:
    """Получает реальный ID по токену"""
    key = f"ref_map:{token}"
    user_id = await redis.get(key)
    if user_id:
        return int(user_id)
    return None