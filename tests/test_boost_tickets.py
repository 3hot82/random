import pytest
from datetime import datetime
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
from core.services.boost_service import BoostService


@pytest.mark.asyncio
class TestBoostTicketsFunctionality:
    """Тесты функционала буст-билетов"""
    
    async def test_grant_boost_ticket_success(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест успешного начисления буст-билета"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "boost_user",
            "full_name": "Boost User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Добавляем пользователя как участника розыгрыша
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new  # Убедимся, что участник успешно добавлен
        
        # Начисляем буст-билет
        success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'Test story boost'
        )
        
        # Проверки
        assert success is True
        
        # Проверяем, что буст-билет добавлен в историю
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'story'
        )
        result = await async_session.execute(stmt)
        boost_ticket = result.scalar_one_or_none()
        
        assert boost_ticket is not None
        assert boost_ticket.comment == 'Test story boost'
        
        # Проверяем, что количество билетов участника увеличилось
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
        assert participant.tickets_count >= 2  # У участника должно быть как минимум 2 билета (1 начальный + 1 буст)
    
    async def test_grant_boost_ticket_duplicate_prevention(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест предотвращения дублирования буст-билетов одного типа"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "no_duplicate_user",
            "full_name": "No Duplicate User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Добавляем пользователя как участника розыгрыша
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new  # Убедимся, что участник успешно добавлен
        
        # Первое начисление буст-билета
        success1 = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'First story boost'
        )
        
        assert success1 is True
        
        # Второе начисление буст-билета того же типа (должно быть отклонено)
        success2 = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',  # Тот же тип
            'Second story boost'
        )
        
        # Проверки
        assert success2 is False  # Второе начисление должно быть отклонено
        
        # Проверяем, что в истории только одно начисление
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id,
            BoostTicket.boost_type == 'story'
        )
        result = await async_session.execute(stmt)
        boost_tickets = result.scalars().all()
        
        assert len(boost_tickets) == 1
        assert boost_tickets[0].comment == 'First story boost'
    
    async def test_boost_ticket_verification(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест проверки возможности получения буст-билета"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "verify_user",
            "full_name": "Verify User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Добавляем пользователя как участника розыгрыша
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new  # Убедимся, что участник успешно добавлен
        
        # Проверяем, может ли пользователь получить буст-билет
        can_receive, reason = await BoostService.can_receive_boost_ticket(
            async_session,
            user.user_id,
            giveaway.id,
            'channel_boost'
        )
        
        # Проверки
        assert can_receive is True
        assert "Можно получить буст-билет" in reason or "can receive" in reason.lower()
        
        # Теперь проверим после получения буст-билета
        success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'channel_boost',
            'Channel boost'
        )
        
        assert success is True
        
        # Снова проверяем возможность получения буст-билета (должна быть отклонена)
        can_receive_after, reason_after = await BoostService.can_receive_boost_ticket(
            async_session,
            user.user_id,
            giveaway.id,
            'channel_boost'
        )
        
        assert can_receive_after is False
        assert "уже получили" in reason_after or "already received" in reason_after.lower()
    
    async def test_boost_ticket_for_non_participant(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест начисления буст-билета для пользователя, который не участвует в розыгрыше"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя (не участника розыгрыша)
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "non_participant_user",
            "full_name": "Non Participant User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Попытка начислить буст-билет пользователю, который не участвует в розыгрыше
        success = await BoostService.grant_boost_ticket(
            async_session, 
            user.user_id, 
            giveaway.id, 
            'story',
            'Test story boost for non-participant'
        )
        
        # Проверки
        assert success is False  # Начисление должно быть отклонено
        
        # Проверяем, что буст-билет не добавлен в историю
        stmt = select(BoostTicket).where(
            BoostTicket.user_id == user.user_id,
            BoostTicket.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        boost_tickets = result.scalars().all()
        
        assert len(boost_tickets) == 0
    
    async def test_get_user_boost_tickets(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест получения списка буст-билетов пользователя"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()
        
        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "get_boosts_user",
            "full_name": "Get Boosts User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()
        
        # Добавляем пользователя как участника розыгрыша
        is_new = await add_participant(async_session, user.user_id, giveaway.id, None, f"TICKET{user.user_id}")
        assert is_new  # Убедимся, что участник успешно добавлен
        
        # Начисляем несколько буст-билетов разных типов
        types = ['story', 'channel_boost', 'referral']
        for i, boost_type in enumerate(types):
            success = await BoostService.grant_boost_ticket(
                async_session, 
                user.user_id, 
                giveaway.id, 
                boost_type,
                f'Test {boost_type}'
            )
            assert success is True
        
        # Проверяем, что все буст-билеты сохранены
        from database.requests.boost_repo import get_user_boost_tickets
        
        # Получаем все буст-билеты пользователя
        all_boosts = await get_user_boost_tickets(async_session, user.user_id)
        assert len(all_boosts) == 3
        
        # Получаем буст-билеты для конкретного розыгрыша
        gw_boosts = await get_user_boost_tickets(async_session, user.user_id, giveaway.id)
        assert len(gw_boosts) == 3
        
        # Проверяем типы буст-билетов
        boost_types = {bt.boost_type for bt in gw_boosts}
        assert boost_types == {'story', 'channel_boost', 'referral'}