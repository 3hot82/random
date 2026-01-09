import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.base import Base
from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.required_channel import GiveawayRequiredChannel
from database.models.participant import Participant
from database.models.winner import Winner


@pytest.fixture(scope="session")
async def engine():
    """Создание асинхронного движка для тестовой базы данных"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def tables(engine):
    """Создание таблиц в тестовой базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_session(engine, tables):
    """Создание асинхронной сессии для тестов"""
    async_session_local = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_local() as session:
        yield session


@pytest.fixture
async def sample_user_data():
    """Образец данных пользователя для тестов"""
    return {
        "user_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "is_premium": False,
        "created_at": datetime.now()
    }


@pytest.fixture
async def sample_giveaway_data():
    """Образец данных розыгрыша для тестов"""
    return {
        "owner_id": 123456789,
        "channel_id": -1001234567890,
        "message_id": 123,
        "prize_text": "Тестовый приз",
        "winners_count": 1,
        "finish_time": datetime.now() + timedelta(days=7),
        "status": "active"
    }


@pytest.fixture
async def sample_channel_data():
    """Образец данных канала для тестов"""
    return {
        "id": -1001234567890,
        "title": "Тестовый канал",
        "link": "https://t.me/test_channel",
        "is_private": False
    }


@pytest.fixture
async def sample_sponsor_data():
    """Образец данных спонсорского канала для тестов"""
    return [
        {"id": -1001111111, "title": "Спонсор 1", "link": "https://t.me/sponsor1"},
        {"id": -10022222222, "title": "Спонсор 2", "link": "https://t.me/sponsor2"}
    ]


@pytest.fixture
async def created_giveaway(async_session, sample_giveaway_data):
    """Создание тестового розыгрыша в базе данных"""
    giveaway = Giveaway(**sample_giveaway_data)
    async_session.add(giveaway)
    await async_session.commit()
    await async_session.refresh(giveaway)
    return giveaway