import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.user import User
from database.models.boost_history import BoostTicket
from database.requests.giveaway_repo import create_giveaway
from database.requests.participant_repo import add_participant
# Removed incorrect import
from handlers.participant.join import try_join_giveaway
from handlers.participant.boost_tickets import handle_story_boost, handle_channel_boost, show_referral_info
from core.services.boost_service import BoostService
from core.services.ref_service import create_ref_link


@pytest.mark.asyncio
class TestParticipationE2E:
    """E2E тесты пользовательских сценариев участия в розыгрышах"""
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_complete_user_participation_journey(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Полный E2E сценарий участия пользователя в розыгрыше"""
        # Настройка моков
        mock_is_subscribed.return_value = True
        mock_get_required_channels.return_value = []
        
        # Подготовка данных - создание розыгрыша
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True
        giveaway.is_captcha_enabled = False
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "e2e_participation_user",
            "full_name": "E2E Participation User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Сценарий 1: Пользователь пытается присоединиться к розыгрышу
        message_mock = AsyncMock()
        message_mock.answer.return_value = None
        message_mock.edit_text.return_value = None
        message_mock.delete.return_value = None
        
        user_mock = MagicMock()
        user_mock.id = user.user_id
        user_mock.username = user.username
        user_mock.first_name = user.full_name.split()[0] if user.full_name else user.username
        user_mock.last_name = ' '.join(user.full_name.split()[1:]) if user.full_name and len(user.full_name.split()) > 1 else ''
        
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
        
        # Выполняем попытку участия
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
        
        # Сценарий 2: Пользователь получает реферальную ссылку
        token = await create_ref_link(user.user_id)
        assert token is not None
        assert len(token) > 0
        
        # Проверяем, что токен можно декодировать
        from core.services.ref_service import resolve_ref_link
        decoded_user_id = await resolve_ref_link(token)
        assert decoded_user_id == user.user_id
        
        # Сценарий 3: Пользователь получает буст-билет
        boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'E2E test story boost'
        )
        
        assert boost_success is True
        
        # Проверяем, что количество билетов увеличилось
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        updated_participant = result.scalar_one_or_none()
        
        assert updated_participant is not None
        assert updated_participant.tickets_count >= 2  # 1 начальный + 1 буст
        
        # Проверяем, что буст-билет записан в историю
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        boost_tickets = result.scalars().all()
        
        assert len(boost_tickets) >= 1
        
        # Сценарий 4: Пользователь проверяет свой статус участия
        is_active = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active is True
    
    async def test_referral_invitation_e2e_flow(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """E2E сценарий приглашения через реферальную систему"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "e2e_referrer",
            "full_name": "E2E Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание пользователя-реферала
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "e2e_referee",
            "full_name": "E2E Referee",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()
        
        # Шаг 1: Реферер становится участником
        referrer_added = await add_participant(
            async_session, 
            referrer.user_id, 
            giveaway.id, 
            None,
            f"TICKET{referrer.user_id}"
        )
        assert referrer_added
        
        # Шаг 2: Реферер получает реферальную ссылку
        token = await create_ref_link(referrer.user_id)
        assert token is not None
        
        # Шаг 3: Реферал переходит по ссылке и становится участником
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
        
        # Шаг 4: Реферер получает буст-билет за приглашение
        boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            referrer.user_id, 
            giveaway.id, 
            'referral',
            f'E2E referral bonus for user {referee.user_id}'
        )
        assert boost_success is True
        
        # Проверяем, что буст-билет записан
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == referrer.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'referral'
        )
        result = await async_session.execute(stmt)
        boost_ticket = result.scalar_one_or_none()
        
        assert boost_ticket is not None
        assert boost_ticket.comment == f'E2E referral bonus for user {referee.user_id}'
        
        # Проверяем, что у реферера увеличилось количество билетов
        stmt = select(Participant).where(
            Participant.user_id == referrer.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referrer_participant = result.scalar_one_or_none()
        
        assert referrer_participant is not None
        assert referrer_participant.tickets_count >= 2  # 1 начальный + 1 за реферала
    
    async def test_boost_ticket_collection_e2e(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """E2E сценарий сбора буст-билетов различными способами"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "e2e_boost_collector",
            "full_name": "E2E Boost Collector",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Пользователь становится участником
        is_new = await add_participant(
            async_session, 
            user.user_id, 
            giveaway.id, 
            None,
            f"TICKET{user.user_id}"
        )
        assert is_new
        
        # Проверяем начальное количество билетов
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        initial_participant = result.scalar_one_or_none()
        initial_tickets = initial_participant.tickets_count if initial_participant else 1
        
        # Сценарий 1: Получение буст-билета за репост сторис
        story_boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'E2E story boost'
        )
        assert story_boost_success is True
        
        # Сценарий 2: Получение буст-билета за буст канала
        channel_boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'channel_boost',
            'E2E channel boost'
        )
        assert channel_boost_success is True
        
        # Проверяем, что количество билетов увеличилось должным образом
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        updated_participant = result.scalar_one_or_none()
        
        assert updated_participant is not None
        # Должно быть как минимум начальное количество + 2 буста
        assert updated_participant.tickets_count >= initial_tickets + 2
        
        # Проверяем, что оба буст-билета записаны в историю
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        boost_tickets = result.scalars().all()
        
        assert len(boost_tickets) >= 2
        
        boost_types = {bt.boost_type for bt in boost_tickets}
        assert 'story' in boost_types
        assert 'channel_boost' in boost_types
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_participation_with_multiple_giveaways_e2e(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, unique_user_id_counter):
        """E2E сценарий участия в нескольких розыгрышах"""
        # Создание нескольких розыгрышей
        giveaways_data = [
            {
                "owner_id": 123456789,
                "channel_id": -1001234567890,
                "message_id": 160,
                "prize_text": "Приз для розыгрыша 1",
                "winners_count": 1,
                "finish_time": datetime.now() + timedelta(days=7),
                "status": "active",
                "is_referral_enabled": True
            },
            {
                "owner_id": 123456789,
                "channel_id": -1001234567891,
                "message_id": 161,
                "prize_text": "Приз для розыгрыша 2",
                "winners_count": 2,
                "finish_time": datetime.now() + timedelta(days=10),
                "status": "active",
                "is_referral_enabled": False
            },
            {
                "owner_id": 123456789,
                "channel_id": -1001234567892,
                "message_id": 162,
                "prize_text": "Приз для розыгрыша 3",
                "winners_count": 3,
                "finish_time": datetime.now() + timedelta(days=14),
                "status": "active",
                "is_referral_enabled": True
            }
        ]
        
        giveaways = []
        for data in giveaways_data:
            giveaway = Giveaway(**data)
            async_session.add(giveaway)
            await async_session.commit()
            giveaways.append(giveaway)
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "multi_giveaway_user",
            "full_name": "Multi Giveaway User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Пользователь участвует во всех розыгрышах
        for i, giveaway in enumerate(giveaways):
            is_new = await add_participant(
                async_session, 
                user.user_id, 
                giveaway.id, 
                None,
                f"TICKET{user.user_id}{i}"
            )
            assert is_new
        
        # Проверяем, что пользователь участвует во всех розыгрышах
        stmt = select(Participant).where(Participant.user_id == user.user_id)
        result = await async_session.execute(stmt)
        user_participants = result.scalars().all()
        
        assert len(user_participants) == 3  # Участник в 3 розыгрышах
        
        # Проверяем, что все участия связаны с правильными розыгрышами
        participant_giveaway_ids = {p.giveaway_id for p in user_participants}
        expected_giveaway_ids = {g.id for g in giveaways}
        assert participant_giveaway_ids == expected_giveaway_ids
        
        # В одном из розыгрышей включена реферальная система, проверим это
        referral_giveaways = [g for g in giveaways if g.is_referral_enabled]
        assert len(referral_giveaways) >= 2
        
        # Проверим, что пользователь может получить реферальную ссылку для розыгрыша с включенной реф. системой
        referral_gw = referral_giveaways[0]
        token = await create_ref_link(user.user_id)
        assert token is not None
        
        # Проверим, что пользователь может получить буст-билет в любом из розыгрышей
        first_giveaway = giveaways[0]
        boost_success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            first_giveaway.id, 
            'story',
            'Multi-giveaway boost'
        )
        assert boost_success is True
        
        # Проверим, что буст-билет записан для конкретного розыгрыша
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == first_giveaway.id
        )
        result = await async_session.execute(stmt)
        boost_ticket = result.scalar_one_or_none()
        
        assert boost_ticket is not None
        assert boost_ticket.boost_type == 'story'
    
    @patch('handlers.participant.join.is_user_subscribed')
    @patch('handlers.participant.join.get_required_channels')
    async def test_participation_status_check_e2e(self, mock_get_required_channels, mock_is_subscribed, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """E2E сценарий проверки статуса участия"""
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
            "username": "status_check_user",
            "full_name": "Status Check User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Проверяем, что пользователь не участвует до присоединения
        is_active_before = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active_before is False
        
        # Добавляем пользователя как участника
        is_new = await add_participant(
            async_session, 
            user.user_id, 
            giveaway.id, 
            None,
            f"TICKET{user.user_id}"
        )
        assert is_new
        
        # Проверяем, что пользователь теперь участвует
        is_active_after = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active_after is True
        
        # Проверяем, что можно получить информацию об участнике
        from database.requests.participant_repo import get_participant_by_user_giveaway
        participant_info = await get_participant_by_user_giveaway(async_session, user.user_id, giveaway.id)
        assert participant_info is not None
        assert participant_info.user_id == user.user_id
        assert participant_info.giveaway_id == giveaway.id
        
        # Проверяем, что можно получить всех участников розыгрыша
        stmt = select(Participant).where(Participant.giveaway_id == giveaway.id)
        result = await async_session.execute(stmt)
        all_participants = result.scalars().all()
        
        assert len(all_participants) == 1
        assert all_participants[0].user_id == user.user_id
        
        # Проверяем, что можно получить всех участников пользователя
        stmt = select(Participant).where(Participant.user_id == user.user_id)
        result = await async_session.execute(stmt)
        user_participations = result.scalars().all()
        
        assert len(user_participations) == 1
        assert user_participations[0].giveaway_id == giveaway.id


# Вспомогательная функция, которая была пропущена в предыдущих тестах
async def is_participant_active(session, user_id, giveaway_id):
    """Проверяет, является ли пользователь активным участником розыгрыша"""
    from database.requests.participant_repo import get_participant_by_user_giveaway
    participant = await get_participant_by_user_giveaway(session, user_id, giveaway_id)
    return participant is not None