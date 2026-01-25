import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch

from database.models.giveaway import Giveaway
from database.models.participant import Participant
from database.models.user import User
from database.requests.participant_repo import add_participant, is_participant_active


@pytest.mark.asyncio
class TestParticipationEdgeCases:
    """Тесты крайних случаев функционала участия в розыгрышах"""

    async def test_prevent_duplicate_participation_same_giveaway(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест предотвращения повторного участия одного пользователя в одном розыгрыше"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()

        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "duplicate_participation_user",
            "full_name": "Duplicate Participation User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Первое участие
        first_participation = await add_participant(
            async_session,
            user.user_id,
            giveaway.id,
            None,  # referrer
            f"TICKET{user.user_id}A"
        )

        # Проверяем, что первое участие прошло успешно
        assert first_participation is True

        # Проверяем, что пользователь стал участником
        is_active = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active is True

        # Повторная попытка участия
        second_participation = await add_participant(
            async_session,
            user.user_id,
            giveaway.id,
            None,  # referrer
            f"TICKET{user.user_id}B"
        )

        # Проверяем, что повторное участие не прошло (должно быть запрещено)
        assert second_participation is False

        # Проверяем, что пользователь все еще числится как участник
        is_still_active = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_still_active is True

        # Проверяем, что в базе только одна запись участника
        stmt = select(Participant).where(
            Participant.user_id == user.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participants = result.scalars().all()
        
        assert len(participants) == 1
        assert participants[0].tickets_count == 1  # Только 1 билет с первой регистрации

    async def test_participation_in_finished_giveaway(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест участия в уже завершенном розыгрыше"""
        # Подготовка данных - создаем завершенный розыгрыш
        finished_giveaway_data = sample_giveaway_data.copy()
        finished_giveaway_data["finish_time"] = datetime.now() - timedelta(days=1)  # Розыгрыш уже закончился
        finished_giveaway_data["status"] = "finished"
        
        giveaway = Giveaway(**finished_giveaway_data)
        async_session.add(giveaway)
        await async_session.commit()

        # Создание пользователя
        user_data = {
            "user_id": unique_user_id_counter(),
            "username": "late_participation_user",
            "full_name": "Late Participation User",
            "is_premium": False,
            "created_at": datetime.now()
        }
        user = User(**user_data)
        async_session.add(user)
        await async_session.commit()

        # Попытка участия в завершенном розыгрыше через low-level функцию
        # Важно: add_participant как низкоуровневая функция не проверяет статус розыгрыша
        # Проверка статуса происходит на уровне бизнес-логики в обработчике
        participation_result = await add_participant(
            async_session,
            user.user_id,
            giveaway.id,
            None,  # referrer
            f"TICKET{user.user_id}"
        )

        # add_participant использует INSERT ... ON CONFLICT DO NOTHING
        # и не проверяет статус розыгрыша, поэтому участие может пройти успешно
        # Проверим, что пользователь стал участником (это реальное поведение low-level функции)
        assert participation_result is True

        # Проверяем, что пользователь стал участником (это показывает, что low-level функция не проверяет статус)
        is_active = await is_participant_active(async_session, user.user_id, giveaway.id)
        assert is_active is True

    async def test_participation_with_referral_in_same_giveaway(self, async_session: AsyncSession, sample_giveaway_data, unique_user_id_counter):
        """Тест участия с рефералом в том же розыгрыше, где пользователь уже участвует"""
        # Подготовка данных
        giveaway = Giveaway(**sample_giveaway_data)
        giveaway.is_referral_enabled = True
        async_session.add(giveaway)
        await async_session.commit()

        # Создание пользователя-реферера
        referrer_data = {
            "user_id": unique_user_id_counter(),
            "username": "referrer_for_duplicate_test",
            "full_name": "Referrer for Duplicate Test",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referrer = User(**referrer_data)
        async_session.add(referrer)
        await async_session.commit()

        # Создание пользователя-реферала
        referee_data = {
            "user_id": unique_user_id_counter(),
            "username": "referee_for_duplicate_test",
            "full_name": "Referee for Duplicate Test",
            "is_premium": False,
            "created_at": datetime.now()
        }
        referee = User(**referee_data)
        async_session.add(referee)
        await async_session.commit()

        # Реферал становится участником без реферера
        first_participation = await add_participant(
            async_session,
            referee.user_id,
            giveaway.id,
            None,  # сначала без реферера
            f"TICKET{referee.user_id}A"
        )
        assert first_participation is True

        # Проверяем, что реферал стал участником
        is_active_before_referral = await is_participant_active(async_session, referee.user_id, giveaway.id)
        assert is_active_before_referral is True

        # Повторная попытка участия с указанием реферера
        second_participation_attempt = await add_participant(
            async_session,
            referee.user_id,
            giveaway.id,
            referrer.user_id,  # теперь пытаемся добавить с реферером
            f"TICKET{referee.user_id}B"
        )

        # Проверяем, что повторная регистрация не прошла
        assert second_participation_attempt is False

        # Проверяем, что реферал все еще участник, но без реферера
        stmt = select(Participant).where(
            Participant.user_id == referee.user_id,
            Participant.giveaway_id == giveaway.id
        )
        result = await async_session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        assert participant is not None
        assert participant.referrer_id is None  # Реферер не был добавлен при повторной попытке