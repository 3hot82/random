import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.user import User
from database.models.boost_history import BoostTicket
from database.requests.giveaway_repo import create_giveaway, get_giveaway_by_id
from database.requests.participant_repo import (
    add_participant, 
    get_participant_by_user_giveaway,
    increment_ticket,
    is_participant_active
)
# Removed incorrect import
from handlers.participant.join import try_join_giveaway
from handlers.participant.boost_tickets import handle_story_boost, handle_channel_boost
from core.services.boost_service import BoostService
from core.services.ref_service import create_ref_link


@pytest.mark.asyncio
class TestParticipationIntegration:
    """Интеграционные тесты для функционала участия в розыгрышах"""
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_full_participation_flow(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Полный интеграционный тест потока участия в розыгрыше"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        giveaway.is_captcha_enabled = False  # Отключаем капчу для теста
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "integration_user",
            "full_name": "Integration User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Имитация участия в розыгрыше
        message_mock = AsyncMock()
        message_mock.answer.return_value = None
        message_mock.edit_text.return_value = None
        
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
        
        # Выполняем полный процесс участия
        await try_join_giveaway(
            call_mock, 
            giveaway.id, 
            async_session, 
            bot_mock, 
            state_mock
        )
        
        # Проверяем, что пользователь стал участником
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
        assert participant.user_id == user.user_id
        assert participant.giveaway_id == giveaway.id
        assert participant.tickets_count >= 1
        
        # Проверяем, что пользователь активен
        is_active = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active is True
        
        # Проверяем, что можно получить участника по пользователю и розыгрышу
        retrieved_participant = await get_participant_by_user_giveaway(async_session, user.user_id, giveaway.id)
        assert retrieved_participant is not None
        assert retrieved_participant.user_id == participant.user_id
        assert retrieved_participant.giveaway_id == participant.giveaway_id
    
    async def test_participation_with_boost_tickets_integration(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Интеграционный тест участия с использованием буст-билетов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "boost_integration_user",
            "full_name": "Boost Integration User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Сначала пользователь должен стать участником
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new
        
        # Проверяем начальное количество билетов
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        initial_tickets = participant.tickets_count if participant else 0
        
        # Начисляем буст-билет за репост сторис
        success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'Integration test story boost'
        )
        
        assert success is True
        
        # Проверяем, что количество билетов увеличилось
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        updated_participant = result.scalar_one_or_none()
        
        assert updated_participant is not None
        assert updated_participant.tickets_count > initial_tickets
        
        # Проверяем, что буст-билет записан в историю
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'story'
        )
        result = await async_session.execute(stmt)
        boost_ticket = result.scalar_one_or_none()
        
        assert boost_ticket is not None
        assert boost_ticket.comment == 'Integration test story boost'
    
    async def test_referral_and_boost_integration(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Интеграционный тест взаимодействия реферальной системы и буст-билетов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "referral_boost_referrer",
            "full_name": "Referral Boost Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание пользователя-реферала
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "referral_boost_referee",
            "full_name": "Referral Boost Referee",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()
        
        # Добавляем реферера как участника
        referrer_added = await add_participant(
            async_session, 
            referrer.user_id, 
            giveaway.id, 
            None,
            f"TICKET{referrer.user_id}"
        )
        assert referrer_added
        
        # Добавляем реферала с указанием реферера
        referee_added = await add_participant(
            async_session, 
            referee.user_id, 
            giveaway.id, 
            referrer.user_id,  # реферер
            f"TICKET{referee.user_id}"
        )
        assert referee_added
        
        # Проверяем связи
        stmt = select(Participant).where(
            Participant.user_id == referee.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referee_participant = result.scalar_one_or_none()
        
        assert referee_participant is not None
        assert referee_participant.referrer_id == referrer.user_id
        
        # Имитация начисления буст-билета рефереру за приглашение
        # (обычно это происходит автоматически при добавлении реферала)
        # Но для теста добавим еще один буст-билет вручную
        success = await BoostService.grant_boost_ticket(
            async_session, 
            referrer.user_id, 
            giveaway.id, 
            'referral',
            f'Referral bonus for inviting user {referee.user_id}'
        )
        
        assert success is True
        
        # Проверяем, что буст-билет добавлен
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == referrer.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'referral'
        )
        result = await async_session.execute(stmt)
        boost_ticket = result.scalar_one_or_none()
        
        assert boost_ticket is not None
        
        # Проверяем, что у реферера увеличилось количество билетов
        stmt = select(Participant).where(
            Participant.user_id == referrer.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referrer_participant = result.scalar_one_or_none()
        
        assert referrer_participant is not None
        assert referrer_participant.tickets_count >= 2  # 1 начальный + 1 за реферала
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_participation_with_captcha_integration(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Интеграционный тест участия с капчей"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_captcha_enabled = True  # Включаем капчу
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "captcha_integration_user",
            "full_name": "Captcha Integration User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Имитация участия в розыгрыше с капчей
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
        
        # Выполняем процесс участия с капчей
        await try_join_giveaway(
            call_mock, 
            giveaway.id, 
            async_session, 
            bot_mock, 
            state_mock
        )
        
        # Проверяем, что состояние установлено на капчу
        # (проверяем, что была попытка установить состояние)
        state_mock.set_state.assert_called()
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_multiple_participation_scenarios(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, unique_user_id_counter):
        """Интеграционный тест нескольких сценариев участия"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Создаем розыгрыш
        sample_giveaway_data = {
            "owner_id": 123456789,
            "channel_id": -1001234567890,
            "message_id": 150,
            "prize_text": "Тестовый приз для интеграционного теста",
            "winners_count": 3,
            "finish_time": datetime.now() + timedelta(days=7),
            "status": "active",
            "is_referral_enabled": True,
            "is_captcha_enabled": False
        }
        
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создаем несколько пользователей
        users_data = [
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_scenario_user1",
                "full_name": "Multi Scenario User1",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_scenario_user2",
                "full_name": "Multi Scenario User2",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "multi_scenario_user3",
                "full_name": "Multi Scenario User3",
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
        
        # Сценарий 1: Первый пользователь участвует напрямую
        user1 = users[0]
        message_mock1 = AsyncMock()
        message_mock1.answer.return_value = None
        
        user_mock1 = MagicMock()
        user_mock1.id = user1.user_id
        
        call_mock1 = AsyncMock()
        call_mock1.from_user = user_mock1
        call_mock1.message = message_mock1
        call_mock1.answer.return_value = None
        
        bot_mock = AsyncMock()
        bot_info_mock = AsyncMock()
        bot_info_mock.username = "testbot"
        bot_mock.get_me.return_value = bot_info_mock
        
        state_mock1 = AsyncMock()
        state_mock1.get_data.return_value = {"gw_id": giveaway.id}
        state_mock1.update_data.return_value = None
        state_mock1.clear.return_value = None
        
        await try_join_giveaway(
            call_mock1, 
            giveaway.id, 
            async_session, 
            bot_mock, 
            state_mock1
        )
        
        # Сценарий 2: Второй пользователь участвует по реферальной ссылке от первого
        user2 = users[1]
        
        # Добавляем второго пользователя как участника с реферером
        is_new = await add_participant(
            async_session, 
            user2.user_id, 
            giveaway.id, 
            user1.user_id,  # реферер
            f"TICKET{user2.user_id}"
        )
        assert is_new
        
        # Сценарий 3: Третий пользователь участвует и получает буст-билет
        user3 = users[2]
        message_mock3 = AsyncMock()
        message_mock3.answer.return_value = None
        
        user_mock3 = MagicMock()
        user_mock3.id = user3.user_id
        
        call_mock3 = AsyncMock()
        call_mock3.from_user = user_mock3
        call_mock3.message = message_mock3
        call_mock3.answer.return_value = None
        
        state_mock3 = AsyncMock()
        state_mock3.get_data.return_value = {"gw_id": giveaway.id}
        state_mock3.update_data.return_value = None
        state_mock3.clear.return_value = None
        
        await try_join_giveaway(
            call_mock3, 
            giveaway.id, 
            async_session, 
            bot_mock, 
            state_mock3
        )
        
        # Добавляем буст-билет третьему пользователю
        boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            user3.user_id, 
            giveaway.id, 
            'story',
            'Test boost for user 3'
        )
        assert boost_success
        
        # Проверяем результаты всех сценариев
        stmt = select(Participant).where(Participant.giveaway_id == giveaway.id)
        result = await async_session.execute(stmt)
        participants = result.scalars().all()
        
        assert len(participants) == 3  # Все три пользователя должны быть участниками
        
        # Проверяем, что у второго пользователя есть реферер
        user2_participant = next((p for p in participants if p.user_id == user2.user_id), None)
        assert user2_participant is not None
        assert user2_participant.referrer_id == user1.user_id
        
        # Проверяем, что у третьего пользователя больше билетов из-за буста
        user3_participant = next((p for p in participants if p.user_id == user3.user_id), None)
        assert user3_participant is not None
        assert user3_participant.tickets_count >= 2  # 1 начальный + 1 буст