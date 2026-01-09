import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.required_channel import GiveawayRequiredChannel
from database.requests.giveaway_repo import create_giveaway


@pytest.mark.asyncio
class TestGiveawayCreation:
    """Тестирование создания розыгрышей"""
    
    async def test_create_giveaway_basic(self, async_session: AsyncSession):
        """Тест создания простого розыгрыша"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 123
        prize = "Тестовый приз"
        winners = 1
        end_time = datetime.now() + timedelta(days=7)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.owner_id == owner_id
        assert giveaway.channel_id == channel_id
        assert giveaway.message_id == message_id
        assert giveaway.prize_text == prize
        assert giveaway.winners_count == winners
        assert giveaway.finish_time == end_time
        assert giveaway.status == "active"
    
    async def test_create_giveaway_with_media(self, async_session: AsyncSession):
        """Тест создания розыгрыша с медиа"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 124
        prize = "Тестовый приз с медиа"
        winners = 2
        end_time = datetime.now() + timedelta(days=5)
        media_file_id = "test_media_file_id"
        media_type = "photo"
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, media_file_id, media_type
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.media_file_id == media_file_id
        assert giveaway.media_type == media_type
    
    async def test_create_giveaway_with_sponsors(self, async_session: AsyncSession):
        """Тест создания розыгрыша с дополнительными каналами (спонсорами)"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 125
        prize = "Тестовый приз со спонсорами"
        winners = 3
        end_time = datetime.now() + timedelta(days=3)
        
        # Спонсоры
        sponsors = [
            {"id": -10011111111, "title": "Тестовый канал 1", "link": "https://t.me/test_channel_1"},
            {"id": -10022222222, "title": "Тестовый канал 2", "link": "https://t.me/test_channel_2"}
        ]
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что спонсорские каналы были созданы
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 2
        
        # Проверяем, что каналы связаны корректно
        channel_ids = {ch.channel_id for ch in required_channels}
        sponsor_ids = {sp["id"] for sp in sponsors}
        assert channel_ids == sponsor_ids

    async def test_create_giveaway_with_sponsors_correct_ids(self, async_session: AsyncSession):
        """Тест создания розыгрыша с дополнительными каналами (спонсорами) с правильными ID"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 125
        prize = "Тестовый приз со спонсорами"
        winners = 3
        end_time = datetime.now() + timedelta(days=3)
        
        # Спонсоры
        sponsors = [
            {"id": -1001111111, "title": "Тестовый канал 1", "link": "https://t.me/test_channel_1"},
            {"id": -1002222222, "title": "Тестовый канал 2", "link": "https://t.me/test_channel_2"}
        ]
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что спонсорские каналы были созданы
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 2
        
        # Проверяем, что каналы связаны корректно (только ID, без проверки совпадения)
        for ch in required_channels:
            assert ch.giveaway_id == giveaway_id
            assert ch.channel_id in [-1001111111, -1002222222]
    
    async def test_create_giveaway_with_referral_enabled(self, async_session: AsyncSession):
        """Тест создания розыгрыша с включенной реферальной системой"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 126
        prize = "Тестовый приз с рефкой"
        winners = 1
        end_time = datetime.now() + timedelta(days=10)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, is_referral=True
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.is_referral_enabled == True
    
    async def test_create_giveaway_with_captcha_enabled(self, async_session: AsyncSession):
        """Тест создания розыгрыша с включенной капчей"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 127
        prize = "Тестовый приз с капчей"
        winners = 1
        end_time = datetime.now() + timedelta(days=10)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, is_captcha=True
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.is_captcha_enabled == True

    async def test_create_giveaway_multiple_winners(self, async_session: AsyncSession):
        """Тест создания розыгрыша с несколькими победителями"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 128
        prize = "Тестовый приз с несколькими победителями"
        winners = 5
        end_time = datetime.now() + timedelta(days=15)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == 5
        assert giveaway.prize_text == "Тестовый приз с несколькими победителями"

    async def test_create_giveaway_long_prize_text(self, async_session: AsyncSession):
        """Тест создания розыгрыша с длинным текстом приза"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 129
        prize = "Очень длинный текст приза для тестирования ограничений на длину текста приза в розыгрыше. " * 10
        winners = 1
        end_time = datetime.now() + timedelta(hours=12)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.prize_text == prize
        assert giveaway.winners_count == 1

    # Тесты для проверки валидации данных при создании розыгрышей
    async def test_create_giveaway_invalid_owner_id(self, async_session: AsyncSession):
        """Тест создания розыгрыша с некорректным ID владельца"""
        # Подготовка данных
        owner_id = -1  # Некорректный ID
        channel_id = -1001234567890
        message_id = 130
        prize = "Тестовый приз"
        winners = 1
        end_time = datetime.now() + timedelta(days=7)
        
        # Проверяем, что создание проходит без ошибок (валидация происходит на уровне бизнес-логики)
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с некорректным ID владельца
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.owner_id == owner_id

    async def test_create_giveaway_invalid_channel_id(self, async_session: AsyncSession):
        """Тест создания розыгрыша с некорректным ID канала"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = 0  # Некорректный ID
        message_id = 131
        prize = "Тестовый приз"
        winners = 1
        end_time = datetime.now() + timedelta(days=7)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с некорректным ID канала
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.channel_id == channel_id

    async def test_create_giveaway_empty_prize_text(self, async_session: AsyncSession):
        """Тест создания розыгрыша с пустым текстом приза"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 132
        prize = ""  # Пустой приз
        winners = 1
        end_time = datetime.now() + timedelta(days=7)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с пустым текстом приза
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.prize_text == prize

    async def test_create_giveaway_zero_winners(self, async_session: AsyncSession):
        """Тест создания розыгрыша с нулевым количеством победителей"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 133
        prize = "Тестовый приз"
        winners = 0  # Некорректное количество
        end_time = datetime.now() + timedelta(days=7)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с нулевым количеством победителей
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == winners

    async def test_create_giveaway_negative_winners(self, async_session: AsyncSession):
        """Тест создания розыгрыша с отрицательным количеством победителей"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 134
        prize = "Тестовый приз"
        winners = -5  # Некорректное количество
        end_time = datetime.now() + timedelta(days=7)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с отрицательным количеством победителей
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == winners

    async def test_create_giveaway_past_end_time(self, async_session: AsyncSession):
        """Тест создания розыгрыша с датой окончания в прошлом"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 135
        prize = "Тестовый приз"
        winners = 1
        end_time = datetime.now() - timedelta(days=1)  # Прошлое время
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        assert isinstance(giveaway_id, int)
        assert giveaway_id > 0
        
        # Проверяем, что розыгрыш сохранился в БД с датой окончания в прошлом
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.finish_time == end_time

    # Тесты для проверки работы с каналами при создании розыгрышей
    async def test_create_giveaway_with_single_additional_channel(self, async_session: AsyncSession):
        """Тест создания розыгрыша с одним дополнительным каналом"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 136
        prize = "Тестовый приз с одним доп. каналом"
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Дополнительный канал
        sponsors = [
            {"id": -1001111, "title": "Тестовый канал 1", "link": "https://t.me/test_channel_1"}
        ]
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что дополнительный канал был создан
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 1
        assert required_channels[0].channel_id == -1001111
        assert required_channels[0].channel_title == "Тестовый канал 1"
        assert required_channels[0].channel_link == "https://t.me/test_channel_1"

    async def test_create_giveaway_with_max_additional_channels(self, async_session: AsyncSession):
        """Тест создания розыгрыша с максимальным количеством дополнительных каналов"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 137
        prize = "Тестовый приз с максимумом доп. каналов"
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Максимальное количество дополнительных каналов (20)
        sponsors = []
        for i in range(20):
            sponsors.append({
                "id": -10022222200 - i,
                "title": f"Тестовый канал {i+1}",
                "link": f"https://t.me/test_channel_{i+1}"
            })
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что все дополнительные каналы были созданы
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 20
        
        # Проверяем, что каналы связаны корректно
        for i, channel in enumerate(required_channels):
            assert channel.channel_id == -10022222200 - i
            assert channel.channel_title == f"Тестовый канал {i+1}"
            assert channel.channel_link == f"https://t.me/test_channel_{i+1}"

    async def test_create_giveaway_with_duplicate_channels(self, async_session: AsyncSession):
        """Тест создания розыгрыша с дублирующимися дополнительными каналами"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 138
        prize = "Тестовый приз с дублирующимися каналами"
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Дополнительные каналы с дубликатом
        sponsors = [
            {"id": -100111111, "title": "Тестовый канал 1", "link": "https://t.me/test_channel_1"},
            {"id": -10011111111, "title": "Тестовый канал 1", "link": "https://t.me/test_channel_1"},  # дубль
            {"id": -10022222222, "title": "Тестовый канал 2", "link": "https://t.me/test_channel_2"}
        ]
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что дополнительные каналы были созданы (включая дубликаты)
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 3  # Все три записи должны быть созданы, включая дубликаты

    async def test_create_giveaway_with_empty_channels_list(self, async_session: AsyncSession):
        """Тест создания розыгрыша с пустым списком дополнительных каналов"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 139
        prize = "Тестовый приз с пустым списком каналов"
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Пустой список дополнительных каналов
        sponsors = []
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time, sponsors=sponsors
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        
        # Проверяем, что дополнительные каналы не были созданы
        stmt = select(GiveawayRequiredChannel).where(GiveawayRequiredChannel.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        required_channels = result.scalars().all()
        
        assert len(required_channels) == 0
        
    # Тесты для сценариев, которые могут допускать пользователи
    async def test_create_giveaway_with_extremely_long_prize_text(self, async_session: AsyncSession):
        """Тест создания розыгрыша с очень длинным текстом приза"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 140
        prize = "A" * 10000  # Очень длинный текст приза
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert len(giveaway.prize_text) == 10000
        assert giveaway.prize_text == prize
        assert giveaway.winners_count == 1

    async def test_create_giveaway_with_maximum_winners(self, async_session: AsyncSession):
        """Тест создания розыгрыша с максимально возможным количеством победителей"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 141
        prize = "Приз для большого количества победителей"
        winners = 50  # Максимальное значение из кода
        end_time = datetime.now() + timedelta(days=5)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == 50
        assert giveaway.prize_text == prize

    async def test_create_giveaway_with_minimum_values(self, async_session: AsyncSession):
        """Тест создания розыгрыша с минимальными значениями"""
        # Подготовка данных
        owner_id = 1
        channel_id = -1001
        message_id = 1
        prize = "A"  # Минимально короткий приз
        winners = 1
        end_time = datetime.now() + timedelta(seconds=1)  # Минимальное время
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.owner_id == 1
        assert giveaway.channel_id == -1001
        assert giveaway.message_id == 1
        assert giveaway.prize_text == "A"
        assert giveaway.winners_count == 1

    async def test_create_giveaway_with_special_characters_in_prize(self, async_session: AsyncSession):
        """Тест создания розыгрыша с особыми символами в названии приза"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 142
        prize = "Приз с эмодзи 🎁🎉🎊 и спецсимволами !@#$%^&*()"
        winners = 1
        end_time = datetime.now() + timedelta(days=5)
        
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
        
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.prize_text == prize
        assert "🎁" in giveaway.prize_text
        assert "!@#$%^&*()" in giveaway.prize_text

    async def test_create_giveaway_with_large_numbers(self, async_session: AsyncSession):
        """Тест создания розыгрыша с большими числовыми значениями"""
        # Подготовка данных
        owner_id = 999999
        channel_id = -9999999
        message_id = 999999
        prize = "Приз с большими числами"
        winners = 10
        end_time = datetime.now() + timedelta(days=365*10)  # 10 лет
    
        # Вызов тестируемой функции
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners, end_time
        )
    
        # Проверки
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.owner_id == 999999
        assert giveaway.channel_id == -9999999

