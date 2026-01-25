import asyncio
from redis.asyncio import Redis
from database import engine, Base
from config import config

# Импортируем ВСЕ модели, чтобы SQLAlchemy знала, что создавать
from database.models.user import User
from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.channel import Channel
from database.models.required_channel import GiveawayRequiredChannel
from database.models.winner import Winner # <--- Важно! Новая таблица
from database.models.boost_history import BoostTicket

async def reset_database():
    print("🗑 Удаляю старые таблицы PostgreSQL...")
    async with engine.begin() as conn:
        # Удаляем все таблицы с использованием CASCADE для разрешения зависимостей
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())  # Удаляем данные
        # Затем удаляем сами таблицы
        await conn.run_sync(Base.metadata.drop_all)
        # Создаем все таблицы заново с новыми полями
        await conn.run_sync(Base.metadata.create_all)
    
    print("🗑 Очищаю Redis...")
    redis = Redis.from_url(config.REDIS_URL)
    await redis.flushdb()
    await redis.aclose()
    
    print("✅ База данных полностью обновлена!")

if __name__ == "__main__":
    asyncio.run(reset_database())