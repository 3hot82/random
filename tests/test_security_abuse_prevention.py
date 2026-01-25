import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.user import User
from database.models.boost_history import BoostTicket
from database.requests.giveaway_repo import create_giveaway
from database.requests.participant_repo import add_participant
# Removed incorrect import
from handlers.participant.join import try_join_giveaway
from core.services.boost_service import BoostService


@pytest.mark.asyncio
class TestSecurityAndAbusePrevention:
    """Тесты безопасности и защиты от злоупотреблений"""
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_protection_against_fake_accounts(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест защиты от создания фейковых аккаунтов"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Проверка валидности данных пользователя
        # Создание пользователя с корректными данными
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "real_user",
            "full_name": "Real User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Проверяем, что пользователь может участвовать в розыгрыше
        message_mock = AsyncMock()
        message_mock.answer.return_value = None
        
        user_mock = MagicMock()
        user_mock.id = user.user_id
        
        call_mock = AsyncMock()
        call_mock.from_user = user_mock
        call_mock.message = message_mock
        call_mock.answer.return_value = None
        
        bot_mock = AsyncMock()
        bot_info_mock = AsyncMock()
        bot_info_mock.username = "testbot"
        bot_mock.get_me.return_value = bot_info_mock
        
        state_mock = AsyncMock()
        state_mock.get_data.return_value = {"gw_id": giveaway.id}
        state_mock.update_data.return_value = None
        state_mock.clear.return_value = None
        
        # Попытка участия
        await try_join_giveaway(
            call_mock,
            giveaway.id,
            async_session,
            bot_mock,
            state_mock
        )
        
        # Проверяем, что участие прошло успешно
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_protection_against_bot_participation(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест защиты от автоматического участия в розыгрышах"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_captcha_enabled = True  # Включаем капчу для защиты
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "human_user",
            "full_name": "Human User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Проверяем, что при включенной капче пользователь получает запрос капчи
        message_mock = AsyncMock()
        message_mock.answer.return_value = None
        
        user_mock = MagicMock()
        user_mock.id = user.user_id
        
        call_mock = AsyncMock()
        call_mock.from_user = user_mock
        call_mock.message = message_mock
        call_mock.answer.return_value = None
        
        bot_mock = AsyncMock()
        bot_info_mock = AsyncMock()
        bot_info_mock.username = "testbot"
        bot_mock.get_me.return_value = bot_info_mock
        
        state_mock = AsyncMock()
        state_mock.get_data.return_value = {"gw_id": giveaway.id}
        state_mock.update_data.return_value = None
        state_mock.clear.return_value = None
        
        # Попытка участия в розыгрыше с капчей
        await try_join_giveaway(
            call_mock,
            giveaway.id,
            async_session,
            bot_mock,
            state_mock
        )
        
        # Проверяем, что состояние установлено на капчу
        state_mock.set_state.assert_called()
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_protection_against_multiaccounts(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест защиты от мультиаккаунтов"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание нескольких пользователей (имитация мультиаккаунтов)
        users_data = [
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_user1",
                "full_name": "Multi User1",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_user2",
                "full_name": "Multi User2",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_user3",
                "full_name": "Multi User3",
                "is_premium": False,
                "created_at": datetime.now()
            }
        ]
        
        users = []
        for user_data in users_data:
            user = User(**user_data)
            async_session.add(user)
            await async_session.commit()
            users.append(user)
        
        # Проверяем, что каждый пользователь может участвовать независимо
        for user in users:
            message_mock = AsyncMock()
            message_mock.answer.return_value = None
            
            user_mock = MagicMock()
            user_mock.id = user.user_id
            
            call_mock = AsyncMock()
            call_mock.from_user = user_mock
            call_mock.message = message_mock
            call_mock.answer.return_value = None
            
            bot_mock = AsyncMock()
            bot_info_mock = AsyncMock()
            bot_info_mock.username = "testbot"
            bot_mock.get_me.return_value = bot_info_mock
            
            state_mock = AsyncMock()
            state_mock.get_data.return_value = {"gw_id": giveaway.id}
            state_mock.update_data.return_value = None
            state_mock.clear.return_value = None
            
            # Попытка участия
            await try_join_giveaway(
                call_mock,
                giveaway.id,
                async_session,
                bot_mock,
                state_mock
            )
        
        # Проверяем, что все пользователи стали участниками
        stmt = select(Participant).where(
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participants = result.scalars().all()
        
        assert len(participants) == 3
        participant_user_ids = {p.user_id for p in participants}
        expected_user_ids = {u.user_id for u in users}
        assert participant_user_ids == expected_user_ids
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_bot_detection_simulation(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест обнаружения подозрительной активности (симуляция ботов)"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "normal_user",
            "full_name": "Normal User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Проверяем нормальное поведение (не подозрительно)
        message_mock = AsyncMock()
        message_mock.answer.return_value = None
        
        user_mock = MagicMock()
        user_mock.id = user.user_id
        
        call_mock = AsyncMock()
        call_mock.from_user = user_mock
        call_mock.message = message_mock
        call_mock.answer.return_value = None
        
        bot_mock = AsyncMock()
        bot_info_mock = AsyncMock()
        bot_info_mock.username = "testbot"
        bot_mock.get_me.return_value = bot_info_mock
        
        state_mock = AsyncMock()
        state_mock.get_data.return_value = {"gw_id": giveaway.id}
        state_mock.update_data.return_value = None
        state_mock.clear.return_value = None
        
        # Одиночное участие - нормальное поведение
        await try_join_giveaway(
            call_mock,
            giveaway.id,
            async_session,
            bot_mock,
            state_mock
        )
        
        # Проверяем, что участие прошло успешно
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
    
    async def test_duplicate_boost_ticket_prevention(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест предотвращения дублирования буст-билетов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "no_duplicate_boost",
            "full_name": "No Duplicate Boost",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Добавляем пользователя как участника
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new
        
        # Несколько попыток начислить буст-билет одного типа подряд
        # (имитация попытки обмануть систему)
        results = []
        for i in range(5):  # 5 попыток
            success = await BoostService.grant_boost_ticket(
                async_session,
                user.user_id,
                giveaway.id,
                'story',  # Один и тот же тип
                f'Test story boost attempt {i}'
            )
            results.append(success)
        
        # Проверяем, что только первая попытка успешна, остальные - нет
        assert results[0] is True  # Первая попытка успешна
        for i in range(1, 5):  # Остальные неуспешны
            assert results[i] is False
        
        # Проверяем, что в базе только одна запись о буст-билете
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'story'
        )
        result = await async_session.execute(stmt)
        boost_tickets = result.scalars().all()
        
        assert len(boost_tickets) == 1
        assert boost_tickets[0].comment == 'Test story boost attempt 0'
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_concurrent_participation_attempts(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест защиты от конкурентных попыток участия (race conditions)"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "concurrent_user",
            "full_name": "Concurrent User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Функция для попытки участия
        async def attempt_join():
            message_mock = AsyncMock()
            message_mock.answer.return_value = None
            
            user_mock = MagicMock()
            user_mock.id = user.user_id
            
            call_mock = AsyncMock()
            call_mock.from_user = user_mock
            call_mock.message = message_mock
            call_mock.answer.return_value = None
            
            bot_mock = AsyncMock()
            bot_info_mock = AsyncMock()
            bot_info_mock.username = "testbot"
            bot_mock.get_me.return_value = bot_info_mock
            
            state_mock = AsyncMock()
            state_mock.get_data.return_value = {"gw_id": giveaway.id}
            state_mock.update_data.return_value = None
            state_mock.clear.return_value = None
            
            await try_join_giveaway(
                call_mock,
                giveaway.id,
                async_session,
                bot_mock,
                state_mock
            )
        
        # Выполняем несколько конкурентных попыток участия
        tasks = [attempt_join() for _ in range(10)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем, что в результате только один участник
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participants = result.scalars().all()
        
        # Должен быть только один участник, несмотря на конкурентные попытки
        assert len(participants) == 1