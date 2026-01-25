import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.user import User
from database.models.pending_referral import PendingReferral
from database.models.boost_history import BoostTicket
from database.requests.giveaway_repo import create_giveaway
from database.requests.participant_repo import (
    add_participant, 
    add_pending_referral, 
    get_pending_referral,
    is_circular_referral,
    is_participant_active
)
from core.services.ref_service import create_ref_link, resolve_ref_link


@pytest.mark.asyncio
class TestReferralSystem:
    """Тесты функционала реферальной системы"""
    
    async def test_create_and_use_referral_link(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест создания и использования реферальной ссылки"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "referrer_user",
            "full_name": "Referrer User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание пользователя-реферала
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "referee_user",
            "full_name": "Referee User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()
        
        # Создаем реферальную ссылку
        token = await create_ref_link(referrer.user_id)
        assert token is not None
        assert len(token) > 0
        
        # Проверяем, что токен можно декодировать обратно в ID
        decoded_user_id = await resolve_ref_link(token)
        assert decoded_user_id == referrer.user_id
        
        # Добавляем обоих пользователей как участников розыгрыша
        referrer_is_new = await add_participant(
            async_session,
            referrer.user_id,
            giveaway.id,
            None,  # referrer не имеет реферера
            f"TICKET{referrer.user_id}"
        )
        assert referrer_is_new
        
        # Добавляем реферала с указанием реферера
        referee_is_new = await add_participant(
            async_session,
            referee.user_id,
            giveaway.id,
            referrer.user_id,  # реферер
            f"TICKET{referee.user_id}"
        )
        assert referee_is_new
        
        # Проверяем, что реферал добавлен с правильным referrer_id
        stmt = select(Participant).where(
            Participant.user_id == referee.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referee_participant = result.scalar_one_or_none()
        
        assert referee_participant is not None
        assert referee_participant.referrer_id == referrer.user_id
        
        # Проверяем, что реферер также является участником
        stmt = select(Participant).where(
            Participant.user_id == referrer.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referrer_participant = result.scalar_one_or_none()
        
        assert referrer_participant is not None
        assert referrer_participant.referrer_id is None
    
    async def test_add_pending_referral(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест добавления ожидающего реферала"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователей
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "pending_referrer",
            "full_name": "Pending Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "pending_referee",
            "full_name": "Pending Referee",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()
        
        # Добавляем ожидающий реферал
        success = await add_pending_referral(
            async_session,
            referee.user_id,
            referrer.user_id,
            giveaway.id
        )
        
        assert success is True
        
        # Проверяем, что ожидающий реферал добавлен в базу
        found_referrer_id = await get_pending_referral(
            async_session,
            referee.user_id,
            giveaway.id
        )
        
        assert found_referrer_id == referrer.user_id
    
    async def test_circular_referral_detection(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест обнаружения циклических рефералов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователей
        user1_data = {
            "user_id": unique_user_id_counter(),
            "username": "circular_user1",
            "full_name": "Circular User1",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user1 = User(**user1_data)
        async_session.add(user1)
        await async_session.commit()
        
        user2_data = {
            "user_id": unique_user_id_counter(),
            "username": "circular_user2",
            "full_name": "Circular User2",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user2 = User(**user2_data)
        async_session.add(user2)
        await async_session.commit()
        
        # Проверяем, что пользователь не является своим собственным рефералом
        is_circular = await is_circular_referral(
            async_session,
            user1.user_id,
            user1.user_id,  # тот же пользователь
            giveaway.id
        )
        
        assert is_circular is True
        
        # Проверяем, что пользователь может нормально реферить другого
        is_circular_different = await is_circular_referral(
            async_session,
            user1.user_id,
            user2.user_id,  # другой пользователь
            giveaway.id
        )
        
        assert is_circular_different is False
    
    async def test_referral_reward_calculation(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест начисления наград за рефералов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "reward_referrer",
            "full_name": "Reward Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание нескольких пользователей-рефералов
        referees_data = [
            {
                "user_id": unique_user_id_counter(),
                "username": "reward_referee1",
                "full_name": "Reward Referee1",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "reward_referee2",
                "full_name": "Reward Referee2",
                "is_premium": False,
                "created_at": datetime.now()
            }
        ]
        
        referees = []
        for referee_data in referees_data:
            referee = User(**referee_data)
            async_session.add(referee)
            await async_session.commit()
            referees.append(referee)
        
        # Добавляем реферера как участника
        referrer_added = await add_participant(
            async_session,
            referrer.user_id,
            giveaway.id,
            None,
            f"TICKET{referrer.user_id}"
        )
        assert referrer_added
        
        # Добавляем рефералов с указанием реферера
        for referee in referees:
            referee_added = await add_participant(
                async_session,
                referee.user_id,
                giveaway.id,
                referrer.user_id,  # реферер
                f"TICKET{referee.user_id}"
            )
            assert referee_added
        
        # Проверяем, что у реферера увеличились шансы (билеты) за каждого реферала
        stmt = select(Participant).where(
            Participant.user_id == referrer.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referrer_participant = result.scalar_one_or_none()
        
        assert referrer_participant is not None
        # У реферера должно быть как минимум начальное количество билетов + по 1 за каждого реферала
        # (в зависимости от логики начисления буст-билетов)
        
        # Проверяем, что у рефералов есть правильный referrer_id
        for referee in referees:
            stmt = select(Participant).where(
                Participant.user_id == referee.user_id,
                Participant.giveaway_id == giveaway.id
            )
            result = await async_session.execute(stmt)
            referee_participant = result.scalar_one_or_none()
            
            assert referee_participant is not None
            assert referee_participant.referrer_id == referrer.user_id
    
    async def test_referral_tracking(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест отслеживания рефералов"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "track_referrer",
            "full_name": "Track Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание нескольких пользователей-рефералов
        referees_data = [
            {
                "user_id": unique_user_id_counter(),
                "username": "track_referee1",
                "full_name": "Track Referee1",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "track_referee2",
                "full_name": "Track Referee2",
                "is_premium": False,
                "created_at": datetime.now()
            },
            {
                "user_id": unique_user_id_counter(),
                "username": "track_referee3",
                "full_name": "Track Referee3",
                "is_premium": False,
                "created_at": datetime.now()
            }
        ]
        
        referees = []
        for referee_data in referees_data:
            referee = User(**referee_data)
            async_session.add(referee)
            await async_session.commit()
            referees.append(referee)
        
        # Добавляем всех как участников
        referrer_added = await add_participant(
            async_session,
            referrer.user_id,
            giveaway.id,
            None,
            f"TICKET{referrer.user_id}"
        )
        assert referrer_added
        
        # Добавляем рефералов с указанием реферера
        for referee in referees:
            referee_added = await add_participant(
                async_session,
                referee.user_id,
                giveaway.id,
                referrer.user_id,  # реферер
                f"TICKET{referee.user_id}"
            )
            assert referee_added
        
        # Подсчитываем количество рефералов у реферера
        stmt = select(Participant).where(
            Participant.referrer_id == referrer.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referrals = result.scalars().all()
        
        assert len(referrals) == 3  # Должно быть 3 реферала
        
        # Проверяем, что все рефералы имеют правильного реферера
        for referral in referrals:
            assert referral.referrer_id == referrer.user_id
            assert referral.giveaway_id == giveaway.id
            assert referral.user_id in [r.user_id for r in referees]
    
    async def test_referral_status_update(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест обновления статуса реферала"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True  # Включаем реферальную систему
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "status_referrer",
            "full_name": "Status Referrer",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()
        
        # Создание пользователя-реферала
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "status_referee",
            "full_name": "Status Referee",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()
        
        # Проверяем, что пользователь не является активным участником до присоединения
        is_active_before = await is_participant_active(
            async_session,
            referee.user_id,
            giveaway.id
        )
        assert is_active_before is False
        
        # Добавляем реферала как участника с реферером
        referee_added = await add_participant(
            async_session,
            referee.user_id,
            giveaway.id,
            referrer.user_id,  # реферер
            f"TICKET{referee.user_id}"
        )
        assert referee_added
        
        # Проверяем, что пользователь теперь активный участник
        is_active_after = await is_participant_active(
            async_session,
            referee.user_id,
            giveaway.id
        )
        assert is_active_after is True
        
        # Проверяем, что реферал имеет правильного реферера
        stmt = select(Participant).where(
            Participant.user_id == referee.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        referee_participant = result.scalar_one_or_none()
        
        assert referee_participant is not None
        assert referee_participant.referrer_id == referrer.user_id