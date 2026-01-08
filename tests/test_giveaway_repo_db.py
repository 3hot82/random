import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

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
async def test_create_giveaway_db(db_session: AsyncSession):
    """Тест создания розыгрыша в базе данных."""
    # Сначала регистрируем пользователя
    owner_id = 12345
    await register_user(db_session, owner_id, "test_user", "Test User")
    
    channel_id = -1001234567890
    message_id = 100
    prize = "Тестовый приз"
    winners = 2
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
    
    # Проверяем, что ID розыгрыша возвращен
    assert giveaway_id is not None
    assert giveaway_id > 0
    
    # Проверяем, что розыгрыш сохранен в базе
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway is not None
    assert giveaway.owner_id == owner_id
    assert giveaway.channel_id == channel_id
    assert giveaway.message_id == message_id
    assert giveaway.prize_text == prize
    assert giveaway.winners_count == winners
    assert giveaway.finish_time == end_time
    assert giveaway.status == "active"


@pytest.mark.asyncio
async def test_get_giveaway_by_id_not_found(db_session: AsyncSession):
    """Тест получения несуществующего розыгрыша."""
    giveaway = await get_giveaway_by_id(db_session, 9999)
    assert giveaway is None


@pytest.mark.asyncio
async def test_get_giveaways_by_owner(db_session: AsyncSession):
    """Тест получения розыгрышей по владельцу."""
    owner_id = 54321
    # Регистрируем пользователя
    await register_user(db_session, owner_id, "test_owner", "Test Owner")
    
    channel_id = -1001234567890
    message_id = 200
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем несколько розыгрышей для одного владельца
    giveaway1_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize="Приз 1",
        winners=1,
        end_time=end_time
    )
    
    giveaway2_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id + 1,
        prize="Приз 2",
        winners=2,
        end_time=end_time
    )
    
    # Создаем розыгрыш для другого владельца
    other_owner_id = 98765
    await register_user(db_session, other_owner_id, "other_user", "Other User")
    await create_giveaway(
        session=db_session,
        owner_id=other_owner_id,
        channel_id=channel_id,
        message_id=message_id + 2,
        prize="Приз другого владельца",
        winners=1,
        end_time=end_time
    )
    
    # Получаем розыгрыши владельца
    giveaways = await get_giveaways_by_owner(db_session, owner_id)
    
    # Проверяем, что получены только розыгрыши нужного владельца
    assert len(giveaways) == 2
    giveaway_ids = [gw.id for gw in giveaways]
    assert giveaway1_id in giveaway_ids
    assert giveaway2_id in giveaway_ids
    
    # Проверяем, что розыгрыши отсортированы по убыванию ID (новые первыми)
    assert giveaways[0].id > giveaways[1].id


@pytest.mark.asyncio
async def test_count_giveaways_by_status(db_session: AsyncSession):
    """Тест подсчета розыгрышей по статусу и владельцу."""
    owner_id = 11111
    # Регистрируем пользователя
    await register_user(db_session, owner_id, "status_user", "Status User")
    
    channel_id = -1001234567890
    message_id = 300
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем активный розыгрыш
    await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize="Активный приз",
        winners=1,
        end_time=end_time
    )
    
    # Создаем завершенный розыгрыш
    finished_giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id + 1,
        prize="Завершенный приз",
        winners=1,
        end_time=datetime.utcnow() - timedelta(days=1)  # Прошедшее время
    )
    
    # Обновляем статус завершенного розыгрыша
    finished_giveaway = await get_giveaway_by_id(db_session, finished_giveaway_id)
    finished_giveaway.status = "finished"
    await db_session.commit()
    
    # Подсчитываем активные розыгрыши
    active_count = await count_giveaways_by_status(db_session, owner_id, "active")
    assert active_count == 1
    
    # Подсчитываем завершенные розыгрыши
    finished_count = await count_giveaways_by_status(db_session, owner_id, "finished")
    assert finished_count == 1
    
    # Подсчитываем все розыгрыши
    total_count = await count_giveaways_by_status(db_session, owner_id, "active") + \
                  await count_giveaways_by_status(db_session, owner_id, "finished")
    assert total_count == 2


@pytest.mark.asyncio
async def test_count_giveaways_by_owner(db_session: AsyncSession):
    """Тест подсчета общего количества розыгрышей по владельцу."""
    owner_id = 222
    # Регистрируем пользователя
    await register_user(db_session, owner_id, "count_user", "Count User")
    
    channel_id = -1001234567890
    message_id = 400
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем несколько розыгрышей для владельца
    for i in range(5):
        await create_giveaway(
            session=db_session,
            owner_id=owner_id,
            channel_id=channel_id,
            message_id=message_id + i,
            prize=f"Приз {i+1}",
            winners=1,
            end_time=end_time
        )
    
    # Подсчитываем общее количество розыгрышей
    count = await count_giveaways_by_owner(db_session, owner_id)
    assert count == 5
    
    # Проверяем, что для другого владельца количество 0
    other_count = await count_giveaways_by_owner(db_session, 99999)
    assert other_count == 0


@pytest.mark.asyncio
async def test_get_active_giveaways(db_session: AsyncSession):
    """Тест получения активных розыгрышей."""
    channel_id = -101234567890
    message_id = 50
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем активный розыгрыш
    active_owner_id = 33333
    await register_user(db_session, active_owner_id, "active_user", "Active User")
    active_giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=active_owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize="Активный приз",
        winners=1,
        end_time=end_time
    )
    
    # Создаем завершенный розыгрыш
    finished_owner_id = 44444
    await register_user(db_session, finished_owner_id, "finished_user", "Finished User")
    finished_giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=finished_owner_id,
        channel_id=channel_id,
        message_id=message_id + 1,
        prize="Завершенный приз",
        winners=1,
        end_time=datetime.utcnow() - timedelta(days=1) # Прошедшее время
    )
    
    # Обновляем статус завершенного розыгрыша
    finished_giveaway = await get_giveaway_by_id(db_session, finished_giveaway_id)
    finished_giveaway.status = "finished"
    await db_session.commit()
    
    # Получаем активные розыгрыши
    active_giveaways = await get_active_giveaways(db_session)
    
    # Проверяем, что возвращен только активный розыгрыш
    assert len(active_giveaways) == 1
    assert active_giveaways[0].id == active_giveaway_id
    assert active_giveaways[0].status == "active"


@pytest.mark.asyncio
async def test_set_predetermined_winner(db_session: AsyncSession):
    """Тест установки предопределенного победителя."""
    owner_id = 55555
    # Регистрируем пользователя
    await register_user(db_session, owner_id, "winner_user", "Winner User")
    
    channel_id = -1001234567890
    message_id = 600
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем розыгрыш
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize="Приз с предустановленным победителем",
        winners=1,
        end_time=end_time
    )
    
    # Проверяем, что изначально нет предопределенного победителя
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway.predetermined_winner_id is None
    
    # Устанавливаем предопределенного победителя
    winner_id = 67890
    await set_predetermined_winner(db_session, giveaway_id, winner_id)
    
    # Проверяем, что победитель установлен
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway.predetermined_winner_id == winner_id


@pytest.mark.asyncio
async def test_giveaway_model_defaults(db_session: AsyncSession):
    """Тест значений по умолчанию для модели розыгрыша."""
    owner_id = 66666
    # Регистрируем пользователя
    await register_user(db_session, owner_id, "default_user", "Default User")
    
    channel_id = -1001234567890
    message_id = 700
    end_time = datetime.utcnow() + timedelta(days=7)
    
    # Создаем розыгрыш с минимальными параметрами
    giveaway_id = await create_giveaway(
        session=db_session,
        owner_id=owner_id,
        channel_id=channel_id,
        message_id=message_id,
        prize="Тест приза",
        winners=1,
        end_time=end_time
    )
    
    # Проверяем значения по умолчанию
    giveaway = await get_giveaway_by_id(db_session, giveaway_id)
    assert giveaway.status == "active"
    assert giveaway.winners_count == 1
    assert giveaway.media_file_id is None
    assert giveaway.media_type is None
    assert giveaway.is_referral_enabled is False
    assert giveaway.is_captcha_enabled is False
    assert giveaway.is_paid is False
    assert giveaway.predetermined_winner_id is None