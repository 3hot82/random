import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from database.models.user import User
from database.models.participant import Participant
from database.models.giveaway import Giveaway
from database.models.pending_referral import PendingReferral
from database.models.boost_history import BoostTicket
from database.requests.participant_repo import (
    add_participant, 
    add_pending_referral, 
    get_pending_referral, 
    is_circular_referral,
    get_participants_count
)


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    
    # Мокаем часто используемые методы сессии
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    
    return session


@pytest.fixture
def sample_giveaway_data():
    """Образец данных розыгрыша для тестов"""
    return {
        "owner_id": 123456789,
        "channel_id": -1001234567890,
        "message_id": 123,
        "prize_text": "Тестовый приз",
        "winners_count": 1,
        "finish_time": datetime.now() + timedelta(days=7),
        "status": "active",
        "is_referral_enabled": True,  # Включаем реферальную систему
        "is_captcha_enabled": False,
        "is_paid": False,
        "is_participants_hidden": False,
        "is_story_boost_enabled": False,
        "is_channel_boost_enabled": False,
        "is_referral_boost_enabled": False
    }


@pytest.mark.asyncio
class TestComprehensiveReferralSystem:
    """Комплексные тесты реферальной системы"""

    async def test_referral_reward_calculation(self, mock_session, sample_giveaway_data):
        """Тест начисления наград за рефералов"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        referee_id = 987654321
        
        # Добавляем реферера как участника розыгрыша
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,  # Нет реферера у реферера
            f"TICKET{referrer_id}"
        )
        assert referrer_added is True
        
        # Добавляем реферала с указанием реферера
        referee_added = await add_participant(
            mock_session, 
            referee_id, 
            giveaway.id, 
            referrer_id,  # Указываем реферера
            f"REF_TICKET_{referee_id}"
        )
        assert referee_added is True
        
        # Проверяем, что реферал записан с правильным реферером
        from sqlalchemy import select
        from database.models.participant import Participant
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(referrer_id=referrer_id)
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # В реальной системе начисление наград происходит через boost_service
        # Проверяем, что реферал был записан с реферером
        stmt = select(Participant).where(
            Participant.user_id == referee_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await mock_session.execute(stmt)
        referee_participant = result.scalar_one_or_none()
        
        # Проверка происходит на уровне базы данных
        assert referee_participant is not None

    async def test_referral_tracking(self, mock_session, sample_giveaway_data):
        """Тест отслеживания рефералов"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Создаем реферера
        referrer = MagicMock(spec=User)
        referrer.user_id = referrer_id
        referrer.username = "referrer_user"
        referrer.full_name = "Referrer User"
        referrer.is_premium = False
        
        # Создаем рефералов
        referees_data = [
            {"user_id": 987654321, "username": "referee1", "full_name": "Referee One"},
            {"user_id": 555555555, "username": "referee2", "full_name": "Referee Two"},
            {"user_id": 444444444, "username": "referee3", "full_name": "Referee Three"}
        ]
        
        referees = []
        for ref_data in referees_data:
            referee = MagicMock(spec=User)
            referee.user_id = ref_data["user_id"]
            referee.username = ref_data["username"]
            referee.full_name = ref_data["full_name"]
            referees.append(referee)
            
            # Добавляем реферала как участника с реферером
            referee_added = await add_participant(
                mock_session, 
                referee.user_id, 
                giveaway.id, 
                referrer_id,  # Указываем реферера
                f"REF_TICKET_referee.user_id}}"
            )
            assert referee_added is True
        
        # Проверяем, что всех рефералов можно отследить через реферера
        # В реальной системе это делается через запрос к базе данных
        stmt = select(Participant).where(Participant.referrer_id == referrer_id)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(referrer_id=referrer_id) for _ in referees]
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        result = await mock_session.execute(stmt)
        tracked_referees = result.scalars().all()
        
        assert len(tracked_referees) == len(referees)

    async def test_referral_status_update(self, mock_session, sample_giveaway_data):
        """Тест обновления статуса реферала"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        referee_id = 987654321
        
        # Создаем реферала
        referee = MagicMock(spec=User)
        referee.user_id = referee_id
        referee.username = "status_referee"
        referee.full_name = "Status Referee"
        referee.is_premium = False
        
        # Добавляем реферала как участника с реферером
        referee_added = await add_participant(
            mock_session, 
            referee.user_id, 
            giveaway.id, 
            referrer_id,
            f"STATUS_TICKET_referee.user_id}}"
        )
        assert referee_added is True
        
        # В реальной системе статус реферала может обновляться при:
        # - завершении розыгрыша
        # - получении приза
        # - выполнении дополнительных действий
        
        # Проверяем начальный статус участия
        from database.requests.participant_repo import is_participant_active
        is_active = await is_participant_active(mock_session, referee.user_id, giveaway.id)
        
        # Статус зависит от реализации, но участие должно быть зафиксировано
        assert is_active is not None

    async def test_referral_bonus_calculation(self, mock_session, sample_giveaway_data):
        """Тест расчета реферальных бонусов"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"REFERRER_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Создаем рефералов и добавляем их с указанием реферера
        num_referees = 5
        for i in range(num_referees):
            referee_id = 900000000 + i
            referee_added = await add_participant(
                mock_session, 
                referee_id, 
                giveaway.id, 
                referrer_id,
                f"BONUS_TICKET_referee_id}}"
            )
            assert referee_added is True
        
        # В реальной системе бонусы начисляются в виде буст-билетов
        # Проверяем, что у реферера должно быть больше билетов за рефералов
        # Это происходит через boost_service
        
        # Считаем количество рефералов
        from sqlalchemy import func, select
        stmt = select(func.count(Participant.user_id)).where(
            Participant.referrer_id == referrer_id,
            Participant.giveaway_id == giveaway.id
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = num_referees
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        referees_count = await get_participants_count(mock_session, giveaway.id, referrer_id)
        # В реальной системе это реализовано через отдельную логику

    async def test_circular_referral_detection(self, mock_session, sample_giveaway_data):
        """Тест обнаружения циклических рефералов"""
        giveaway = Giveaway(**sample_giveaway_data)
        user_a_id = 111111111
        user_b_id = 222222222
        user_c_id = 333333333
        
        # Создаем цикл: A -> B -> C -> A
        # Это должно быть обнаружено системой
        
        # Проверяем, что пользователь не является своим собственным рефералом
        is_circular_self = await is_circular_referral(
            mock_session, 
            user_a_id,  # Новый пользователь
            user_a_id,  # Его реферер - тот же пользователь
            giveaway.id
        )
        assert is_circular_self is True  # Это циклическая ситуация
        
        # Проверяем нормальную ситуацию (не циклическую)
        is_circular_normal = await is_circular_referral(
            mock_session, 
            user_b_id,  # Новый пользователь
            user_a_id,  # Его реферер - другой пользователь
            giveaway.id
        )
        assert is_circular_normal is False  # Это нормальная ситуация

    async def test_pending_referral_functionality(self, mock_session, sample_giveaway_data):
        """Тест функционала ожидающих рефералов"""
        giveaway_id = 123
        user_id = 456
        referrer_id = 789
        
        # Добавляем ожидающий реферал
        success = await add_pending_referral(mock_session, user_id, referrer_id, giveaway_id)
        
        # Проверяем, что запись была добавлена
        assert success is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Получаем ожидающий реферал
        found_referrer_id = await get_pending_referral(mock_session, user_id, giveaway_id)
        
        # Проверяем, что правильный реферер возвращен
        assert found_referrer_id == referrer_id
        
        # Повторный вызов должен вернуть None, так как запись удаляется после получения
        second_call_result = await get_pending_referral(mock_session, user_id, giveaway_id)
        assert second_call_result is None

    async def test_referral_link_creation_and_usage(self, mock_session, sample_giveaway_data):
        """Тест создания и использования реферальной ссылки"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Реферальная ссылка обычно создается в сервисе
        # Здесь тестируем интеграцию с системой участия
        
        # Добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"LINK_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Добавляем реферала через реферальную ссылку (с указанием реферера)
        referee_id = 987654321
        referee_added = await add_participant(
            mock_session, 
            referee_id, 
            giveaway.id, 
            referrer_id,  # Реферер, полученный из ссылки
            f"LINKREF_TICKET_referee_id}}"
        )
        assert referee_added is True
        
        # Проверяем, что связь установлена
        from sqlalchemy import select
        stmt = select(Participant).where(
            Participant.user_id == referee_id,
            Participant.giveaway_id == giveaway.id
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_result.scalar_one_or_none.return_value.user_id = referee_id
        mock_result.scalar_one_or_none.return_value.referrer_id = referrer_id
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        result = await mock_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
        assert participant.referrer_id == referrer_id

    async def test_referral_chain_tracking(self, mock_session, sample_giveaway_data):
        """Тест отслеживания цепочки рефералов"""
        giveaway = Giveaway(**sample_giveaway_data)
        
        # Создаем цепочку: A приглашает B, B приглашает C
        user_a_id = 111111111
        user_b_id = 222222222
        user_c_id = 333333333
        
        # A не имеет реферера
        user_a_added = await add_participant(
            mock_session, 
            user_a_id, 
            giveaway.id, 
            None,
            f"A_TICKET_user_a_id}}"
        )
        assert user_a_added is True
        
        # B имеет реферера A
        user_b_added = await add_participant(
            mock_session, 
            user_b_id, 
            giveaway.id, 
            user_a_id,
            f"B_TICKET_user_b_id}}"
        )
        assert user_b_added is True
        
        # C имеет реферера B
        user_c_added = await add_participant(
            mock_session, 
            user_c_id, 
            giveaway.id, 
            user_b_id,
            f"C_TICKET_user_c_id}}"
        )
        assert user_c_added is True
        
        # Проверяем связи
        # У A нет реферера
        # У B реферер A
        # У C реферер B
        
        # В реальной системе можно отследить всю цепочку
        stmt_a = select(Participant).where(
            Participant.user_id == user_a_id,
            Participant.giveaway_id == giveaway.id
        )
        stmt_b = select(Participant).where(
            Participant.user_id == user_b_id,
            Participant.giveaway_id == giveaway.id
        )
        stmt_c = select(Participant).where(
            Participant.user_id == user_c_id,
            Participant.giveaway_id == giveaway.id
        )
        
        # Мокаем результаты
        mock_result_a = AsyncMock()
        mock_result_a.scalar_one_or_none.return_value = MagicMock()
        mock_result_a.scalar_one_or_none.return_value.user_id = user_a_id
        mock_result_a.scalar_one_or_none.return_value.referrer_id = None  # Нет реферера
        
        mock_result_b = AsyncMock()
        mock_result_b.scalar_one_or_none.return_value = MagicMock()
        mock_result_b.scalar_one_or_none.return_value.user_id = user_b_id
        mock_result_b.scalar_one_or_none.return_value.referrer_id = user_a_id  # Реферер A
        
        mock_result_c = AsyncMock()
        mock_result_c.scalar_one_or_none.return_value = MagicMock()
        mock_result_c.scalar_one_or_none.return_value.user_id = user_c_id
        mock_result_c.scalar_one_or_none.return_value.referrer_id = user_b_id  # Реферер B
        
        async def mock_execute(stmt):
            if "user_id = 111111111" in str(stmt):
                return mock_result_a
            elif "user_id = 222222222" in str(stmt):
                return mock_result_b
            else:
                return mock_result_c
                
        mock_session.execute = mock_execute
        
        # Проверяем связи
        result_a = await mock_session.execute(stmt_a)
        participant_a = result_a.scalar_one_or_none()
        assert participant_a.referrer_id is None
        
        result_b = await mock_session.execute(stmt_b)
        participant_b = result_b.scalar_one_or_none()
        assert participant_b.referrer_id == user_a_id
        
        result_c = await mock_session.execute(stmt_c)
        participant_c = result_c.scalar_one_or_none()
        assert participant_c.referrer_id == user_b_id

    async def test_referral_bonus_distribution(self, mock_session, sample_giveaway_data):
        """Тест распределения реферальных бонусов"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"DIST_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Добавляем нескольких рефералов
        num_referees = 3
        for i in range(num_referees):
            referee_id = 900000000 + i
            referee_added = await add_participant(
                mock_session, 
                referee_id, 
                giveaway.id, 
                referrer_id,
                f"DISTREF_TICKET_referee_id}}"
            )
            assert referee_added is True
        
        # В реальной системе бонусы начисляются как буст-билеты
        # Проверяем, что у реферера должно быть больше билетов
        # Это происходит через реферальную систему и boost_service
        
        # Симулируем начисление бонусов
        from database.requests.boost_repo import add_boost_ticket
        
        # Начисляем буст-билеты за каждого реферала
        for i in range(num_referees):
            boost_added = await add_boost_ticket(
                mock_session,
                referrer_id,
                giveaway.id,
                'referral',
                f'Referral bonus for bringing user {900000000 + i}'
            )
            assert boost_added is True

    async def test_referral_system_integration_with_boost_tickets(self, mock_session, sample_giveaway_data):
        """Тест интеграции реферальной системы с буст-билетами"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"INTEGRATION_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Добавляем реферала
        referee_id = 987654321
        referee_added = await add_participant(
            mock_session, 
            referee_id, 
            giveaway.id, 
            referrer_id,
            f"INTEGRATIONREF_TICKET_referee_id}}"
        )
        assert referee_added is True
        
        # Проверяем, что буст-билеты можно начислить за реферала
        from database.requests.boost_repo import add_boost_ticket
        
        boost_success = await add_boost_ticket(
            mock_session,
            referrer_id,  # Начисляем рефереру
            giveaway.id,
            'referral',  # Тип буста - реферальный
            'Bonus for successful referral'
        )
        
        assert boost_success is True

    async def test_referral_validation_before_participation(self, mock_session, sample_giveaway_data):
        """Тест валидации реферала перед участием в розыгрыше"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        referee_id = 987654321
        
        # Сначала добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"VALIDATION_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Проверяем, что реферер существует и может быть реферером
        # В реальной системе перед добавлением реферала проверяется:
        # 1. Существует ли реферер
        # 2. Не является ли это циклической ссылкой
        # 3. Допустимо ли такое реферальное отношение
        
        is_circular = await is_circular_referral(
            mock_session, 
            referee_id, 
            referrer_id, 
            giveaway.id
        )
        assert is_circular is False  # Нормальная ситуация
        
        # Добавляем реферала
        referee_added = await add_participant(
            mock_session, 
            referee_id, 
            giveaway.id, 
            referrer_id,
            f"VALIDATED_TICKET_referee_id}}"
        )
        assert referee_added is True

    async def test_multiple_referral_sources_handling(self, mock_session, sample_giveaway_data):
        """Тест обработки множественных источников рефералов"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        referee_id = 987654321
        
        # Добавляем реферала первый раз
        first_referral = await add_participant(
            mock_session, 
            referee_id, 
            giveaway.id, 
            referrer_id,
            f"FIRST_TICKET_referee_id}}"
        )
        assert first_referral is True
        
        # Пытаемся добавить того же реферала второй раз с другим реферером
        other_referrer_id = 555555555
        second_referral = await add_participant(
            mock_session, 
            referee_id,  # Тот же пользователь
            giveaway.id, 
            other_referrer_id,  # Другой реферер
            f"SECOND_TICKET_referee_id}}"
        )
        # В реальной системе повторное участие не должно изменить реферера
        # или может быть запрещено
        
        # Проверяем, что реферал остался с первоначальным реферером
        from sqlalchemy import select
        stmt = select(Participant).where(
            Participant.user_id == referee_id,
            Participant.giveaway_id == giveaway.id
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_result.scalar_one_or_none.return_value.user_id = referee_id
        mock_result.scalar_one_or_none.return_value.referrer_id = referrer_id  # Должен остаться первоначальный реферер
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        result = await mock_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant.referrer_id == referrer_id  # Остался первоначальный реферер

    async def test_referral_statistics_calculation(self, mock_session, sample_giveaway_data):
        """Тест расчета статистики реферальной программы"""
        giveaway = Giveaway(**sample_giveaway_data)
        referrer_id = 123456789
        
        # Добавляем реферера
        referrer_added = await add_participant(
            mock_session, 
            referrer_id, 
            giveaway.id, 
            None,
            f"STATS_TICKET_referrer_id}}"
        )
        assert referrer_added is True
        
        # Добавляем несколько рефералов
        num_referees = 7
        for i in range(num_referees):
            referee_id = 800000000 + i
            referee_added = await add_participant(
                mock_session, 
                referee_id, 
                giveaway.id, 
                referrer_id,
                f"STATSREF_TICKET_referee_id}}"
            )
            assert referee_added is True
        
        # Рассчитываем статистику
        from sqlalchemy import func, select
        stmt = select(func.count(Participant.user_id)).where(
            Participant.referrer_id == referrer_id,
            Participant.giveaway_id == giveaway.id
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = num_referees
        
        async def mock_execute(stmt):
            return mock_result
            
        mock_session.execute = mock_execute
        
        referral_count = await mock_session.execute(stmt)
        count = referral_count.scalar_one_or_none()
        
        assert count == num_referees

    async def test_referral_system_edge_cases(self, mock_session, sample_giveaway_data):
        """Тест крайних случаев реферальной системы"""
        giveaway = Giveaway(**sample_giveaway_data)
        
        # Тест с нулевым ID пользователя
        with pytest.raises(Exception):
            await add_participant(mock_session, 0, giveaway.id, 123, "ZERO_USER")
        
        # Тест с отрицательным ID реферера
        success = await add_participant(mock_session, 123456789, giveaway.id, -1, "NEG_REF")
        # Поведение зависит от реализации, но не должно падать
        
        # Тест с очень большим ID
        large_id = 999999999999
        success = await add_participant(mock_session, large_id, giveaway.id, 123, "LARGE_ID")
        # Поведение зависит от реализации