# database/__init__.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import config
from .base import Base
# Импорт моделей
from .models.user import User
from .models.giveaway import Giveaway
from .models.participant import Participant
from .models.channel import Channel
from .models.required_channel import GiveawayRequiredChannel
from .models.winner import Winner # <--- НОВОЕ

engine = create_async_engine(
    url=config.DB_DNS,
    echo=False,
    pool_pre_ping=True
)

async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)