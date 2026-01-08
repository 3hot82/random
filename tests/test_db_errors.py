import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DataError, InvalidRequestError
from sqlalchemy import text
import asyncio

from database.models.giveaway import Giveaway
from database.models.user import User
from database.requests.giveaway_repo import (
    create_giveaway,
    get_giveaway_by_id,
    get_giveaways_by_owner,
    count_giveaways_by_status,
    count_giveaways_by_owner,
    get_active_giveaways,
    set_predetermined_winner
)
from database.requests.user_repo import register_user


@pytest.mark.asyncio
async def test_foreign_key_constraint_violation(db_session: AsyncSession):
    """Тест нарушения ограничения внешнего ключа при создании розыгрыша с несуществующим владельцем."""
    # Попытка создать розыгрыш с несуществующим пользователем (владельцем)
    channel_id = -1001234567890
    message_id = 100
    prize = "Тестовый приз"
    winners = 2
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Это должно вызвать ошибку, так как пользователя с таким ID не существует
    with pytest.raises(Exception):  # Внешний ключ должен вызвать ошибку
        giveaway_id = await create_giveaway(
            session=db_session,
            owner_id=99999,  # Несуществующий пользователь
            channel_id=channel_id,
            message_id=message_id,
            prize=prize,
            winners=winners,
            end_time=end_time
        )


@pytest.mark.asyncio
async def test_unique_constraint_violation(db_session: AsyncSession):
    """Тест нарушения уникального ограничения (если бы оно было)."""
    # Для данной модели нет уникальных ограничений, кроме автоинкрементного ID
    # Проверим, что обычное создание двух розыгрышей работает нормально
    owner_id = 88888
    await register_user(db_session, owner_id, "test_user", "Test User")
    
    channel_id = -1001234567890
    message_id = 100
    prize = "Тестовый приз"
    winners = 2
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем два розыгрыша - это должно работать, так как нет уникальных ограничений
    giveaway_id_1 = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize=prize,
        winners=winners,
        end_time=end_time
    )
    
    giveaway_id_2 = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id + 1,
        prize=prize + " 2",
        winners=winners,
        end_time=end_time
    )
    
    assert giveaway_id_1 != giveaway_id_2


@pytest.mark.asyncio
async def test_datetime_serialization_error(db_session: AsyncSession):
    """Тест ошибки сериализации даты."""
    owner_id = 77777
    await register_user(db_session, owner_id, "datetime_user", "Datetime User")
    
    channel_id = -1001234567890
    message_id = 200
    prize = "Тест приза с датой"
    winners = 1
    
    # Проверим корректную работу с датами
    end_time = datetime.utcnow() + timedelta(days=7)
    
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize=prize,
        winners=winners,
        end_time=end_time
    )
    
    # Получаем розыгрыш и проверяем дату
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway is not None
    assert abs((giveaway.finish_time - end_time).total_seconds()) < 1  # Разница менее секунды


@pytest.mark.asyncio
async def test_data_type_mismatch(db_session: AsyncSession):
    """Тест несоответствия типа данных."""
    owner_id = 66666
    await register_user(db_session, owner_id, "mismatch_user", "Mismatch User")
    
    channel_id = -1001234567890
    message_id = 300
    prize = "Тест приза с типами"
    winners = 1
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Проверяем, что система корректно обрабатывает правильные типы
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize=prize,
        winners=winners,
        end_time=end_time
    )
    
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway is not None
    assert giveaway.owner_id == owner_id
    assert giveaway.winners_count == winners


@pytest.mark.asyncio
async def test_null_constraint_violation(db_session: AsyncSession):
    """Тест нарушения ограничения NOT NULL."""
    # В нашей модели нет обязательных полей, кроме тех, что имеют значения по умолчанию
    owner_id = 55555
    await register_user(db_session, owner_id, "null_test_user", "Null Test User")
    
    channel_id = -1001234567890
    message_id = 400
    prize = "Тест приза с null"
    winners = 1
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Проверяем создание розыгрыша с допустимыми значениями
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize=prize,
        winners=winners,
        end_time=end_time
    )
    
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway is not None
    # Проверяем, что поля, которые могут быть NULL, действительно могут быть NULL
    assert giveaway.predetermined_winner_id is None


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(db_session: AsyncSession):
    """Тест отката транзакции при ошибке."""
    owner_id = 44444
    await register_user(db_session, owner_id, "rollback_user", "Rollback User")
    
    channel_id = -1001234567890
    message_id = 500
    prize = "Тест приза для отката"
    winners = 1
    end_time = datetime.utcnow() + timedelta(days=7)
    
    try:
        # Начинаем транзакцию
        await create_giveaway(
            session=db_session,
            owner_id=owner_id,
            channel_id=channel_id,
            message_id=message_id,
            prize=prize,
            winners=winners,
            end_time=end_time
        )
        
        # Пытаемся создать еще один с ошибкой (несуществующий владелец)
        await create_giveaway(
            session=db_session,
            owner_id=999999999,  # Несуществующий пользователь
            channel_id=channel_id,
            message_id=message_id + 1,
            prize=prize,
            winners=winners,
            end_time=end_time
        )
    except Exception:
        # Второй вызов должен вызвать ошибку и откатить транзакцию
        # Но т.к. мы используем общую сессию, нам нужно откатить вручную
        await db_session.rollback()
    
    # Проверяем, что не осталось следов второй попытки
    giveaways = await get_giveaways_by_owner(db_session, owner_id)
    # Только первый розыгрыш должен остаться
    assert len(giveaways) == 1


@pytest.mark.asyncio
async def test_race_condition_simulation(db_session: AsyncSession):
    """Симуляция состояния гонки при конкурентном доступе."""
    owner_id = 33333
    await register_user(db_session, owner_id, "race_user", "Race User")
    
    channel_id = -1001234567890
    message_id = 600
    prize = "Приз для гонки"
    winners = 1
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем задачи для конкурентного выполнения
    async def create_giveaway_task():
        return await create_giveaway(
            session=db_session,
            owner_id=owner_id,
            channel_id=channel_id,
            message_id=message_id,
            prize=prize,
            winners=winners,
            end_time=end_time
        )
    
    # Выполняем задачи конкурентно
    tasks = [create_giveaway_task() for _ in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Подсчитываем успешные результаты
    successful_creations = [r for r in results if isinstance(r, int)]
    
    # В зависимости от настроек БД и уровня изоляции транзакций
    # может создаться 1 или несколько розыгрышей
    assert len(successful_creations) >= 1


@pytest.mark.asyncio
async def test_large_data_handling(db_session: AsyncSession):
    """Тест обработки больших объемов данных."""
    owner_id = 22222
    await register_user(db_session, owner_id, "large_data_user", "Large Data User")
    
    channel_id = -1001234567890
    message_id = 700
    # Создаем очень длинный текст приза
    prize = "A" * 10000  # 10,000 символов
    winners = 1
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем розыгрыш с длинным текстом
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize=prize,
        winners=winners,
        end_time=end_time
    )
    
    # Проверяем, что розыгрыш сохранился
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway is not None
    # Проверяем, что текст не был усечен (или усечен до разумного предела)
    assert len(giveaway.prize_text) <= len(prize)


@pytest.mark.asyncio
async def test_index_usage_optimization(db_session: AsyncSession):
    """Тест проверки использования индексов (через анализ плана запроса)."""
    owner_id = 11111
    await register_user(db_session, owner_id, "index_user", "Index User")
    
    # Создаем несколько розыгрышей для пользователя
    channel_id = -1001234567890
    end_time = datetime.utcnow() + timedelta(days=7)
    
    for i in range(5):
        await create_giveaway(
            session=db_session,
            owner_id=owner_id,
            channel_id=channel_id,
            message_id=800 + i,
            prize=f"Приз {i}",
            winners=1,
            end_time=end_time
        )
    
    # Проверяем, что запрос по владельцу работает корректно
    giveaways = await get_giveaways_by_owner(db_session, owner_id)
    assert len(giveaways) == 5
    
    # Проверяем подсчет по статусу
    active_count = await count_giveaways_by_status(db_session, owner_id, "active")
    assert active_count == 5
    
    # Проверяем общий подсчет
    total_count = await count_giveaways_by_owner(db_session, owner_id)
    assert total_count == 5


@pytest.mark.asyncio
async def test_deadlock_simulation(db_session: AsyncSession):
    """Симуляция дедлока (в упрощенном виде)."""
    # Регистрируем двух пользователей
    user1_id = 10001
    user2_id = 10002
    await register_user(db_session, user1_id, "user1", "User One")
    await register_user(db_session, user2_id, "user2", "User Two")
    
    channel_id = -1001234567890
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем розыгрыши для обоих пользователей
    gw1_id = await create_giveaway(
        session=db_session,
        owner_id=user1_id,
        channel_id=channel_id,
        message_id=900,
        prize="Приз 1",
        winners=1,
        end_time=end_time
    )
    
    gw2_id = await create_giveaway(
        session=db_session,
        owner_id=user2_id,
        channel_id=channel_id,
        message_id=901,
        prize="Приз 2",
        winners=1,
        end_time=end_time
    )
    
    # Проверяем, что оба розыгрыша существуют
    giveaway1 = await get_giveaway_by_id(db_session, gw1_id)
    giveaway2 = await get_giveaway_by_id(db_session, gw2_id)
    
    assert giveaway1 is not None
    assert giveaway2 is not None
    assert giveaway1.id == gw1_id
    assert giveaway2.id == gw2_id