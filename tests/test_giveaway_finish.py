import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.participant import Participant
from database.models.winner import Winner
from database.requests.giveaway_repo import create_giveaway
from core.logic.randomizer import select_winners


@pytest.mark.asyncio
class TestGiveawayFinish:
    """Тестирование завершения розыгрышей и уведомлений"""

    async def test_giveaway_finish_and_notify_winner(self, async_session: AsyncSession):
        """Тест завершения розыгрыша и уведомления победителя"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 123
        prize = "Тестовый приз"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание участников
        participants = []
        for i in range(5):
            user_id = 987654321 + i
            username = f"test_user{i}"
            
            # Создаем или обновляем пользователя
            user = await async_session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=f"Test{i}",
                    last_name=f"User{i}",
                    is_premium=False
                )
                async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=user_id,
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
            participants.append(user_id)
        
        await async_session.commit()
        
        # Проверяем, что розыгрыш создан
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.status == "active"
        
        # Тестируем выбор победителей
        selected_winners = select_winners(giveaway, participants)
        assert len(selected_winners) == min(winners_count, len(participants))
        
        # Проверяем, что победитель выбран из списка участников
        for winner_id in selected_winners:
            assert winner_id in participants
        
        # Проверяем, что победители сохраняются в базе
        for winner_id in selected_winners:
            winner = Winner(
                user_id=winner_id,
                giveaway_id=giveaway_id,
                win_date=datetime.now()
            )
            async_session.add(winner)
        
        # Обновляем статус розыгрыша на "завершен"
        giveaway.status = "finished"
        await async_session.commit()
        
        # Проверяем, что статус обновился
        updated_giveaway = await async_session.get(Giveaway, giveaway_id)
        assert updated_giveaway.status == "finished"
        
        # Проверяем, что победители сохранены
        stmt = select(Winner).where(Winner.giveaway_id == giveaway_id)
        result = await async_session.execute(stmt)
        winners = result.scalars().all()
        assert len(winners) == len(selected_winners)
        
        # Проверяем, что каждый победитель из списка выбранных победителей
        winner_ids = [w.user_id for w in winners]
        for winner_id in selected_winners:
            assert winner_id in winner_ids

    async def test_giveaway_finish_multiple_winners(self, async_session: AsyncSession):
        """Тест завершения розыгрыша с несколькими победителями"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 124
        prize = "Приз для нескольких победителей"
        winners_count = 3
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание участников (больше, чем победителей)
        participants = []
        for i in range(10):
            user_id = 987654321 + i
            username = f"test_user{i}"
            
            # Создаем или обновляем пользователя
            user = await async_session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=f"Test{i}",
                    last_name=f"User{i}",
                    is_premium=False
                )
                async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=user_id,
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
            participants.append(user_id)
        
        await async_session.commit()
        
        # Проверяем, что розыгрыш создан
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == winners_count
        
        # Тестируем выбор победителей
        selected_winners = select_winners(giveaway, participants)
        assert len(selected_winners) == winners_count  # Должно быть ровно 3 победителя
        
        # Проверяем, что все победители из списка участников
        for winner_id in selected_winners:
            assert winner_id in participants
        
        # Проверяем, что нет повторяющихся победителей
        assert len(set(selected_winners)) == len(selected_winners)

    async def test_giveaway_finish_with_predetermined_winner(self, async_session: AsyncSession):
        """Тест завершения розыгрыша с заранее определенным победителем"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 125
        prize = "Подкрученный приз"
        winners_count = 2
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        predetermined_winner_id = 9999999  # Задаем конкретного победителя
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Устанавливаем предопределенного победителя
        from database.requests.giveaway_repo import set_predetermined_winner
        await set_predetermined_winner(async_session, giveaway_id, predetermined_winner_id)
        
        # Обновляем розыгрыш в сессии
        giveaway = await async_session.get(Giveaway, giveaway_id)
        
        # Создание участников (включая предопределенного победителя)
        participants = [predetermined_winner_id]  # Добавляем предопределенного победителя
        for i in range(5):
            user_id = 987654321 + i
            username = f"test_user{i}"
            
            # Создаем или обновляем пользователя
            user = await async_session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=f"Test{i}",
                    last_name=f"User{i}",
                    is_premium=False
                )
                async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=user_id,
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
            participants.append(user_id)
        
        await async_session.commit()
        
        # Обновляем розыгрыш в сессии после установки предопределенного победителя
        giveaway = await async_session.get(Giveaway, giveaway_id)
        
        # Тестируем выбор победителей
        selected_winners = select_winners(giveaway, participants)
        
        # Проверяем, что предопределенный победитель включен
        assert predetermined_winner_id in selected_winners
        assert len(selected_winners) == winners_count
        
        # Проверяем, что остальные победители выбраны случайно из оставшихся
        other_winners = [w for w in selected_winners if w != predetermined_winner_id]
        assert len(other_winners) == winners_count - 1
        
        for winner_id in other_winners:
            assert winner_id in participants

    async def test_giveaway_finish_not_enough_participants(self, async_session: AsyncSession):
        """Тест завершения розыгрыша когда участников меньше чем победителей"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 126
        prize = "Приз когда мало участников"
        winners_count = 5  # Больше победителей чем участников
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание участников (меньше чем победителей)
        participants = []
        for i in range(3):  # Только 3 участника
            user_id = 987654321 + i
            username = f"test_user{i}"
            
            # Создаем или обновляем пользователя
            user = await async_session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=f"Test{i}",
                    last_name=f"User{i}",
                    is_premium=False
                )
                async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=user_id,
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
            participants.append(user_id)
        
        await async_session.commit()
        
        # Проверяем, что розыгрыш создан
        giveaway = await async_session.get(Giveaway, giveaway_id)
        assert giveaway is not None
        assert giveaway.winners_count == 5  # Ожидаем 5 победителей
        
        # Тестируем выбор победителей
        selected_winners = select_winners(giveaway, participants)
        
        # Когда участников меньше чем победителей, все участники становятся победителями
        assert len(selected_winners) == len(participants)  # 3, а не 5
        assert set(selected_winners) == set(participants)

    async def test_giveaway_finish_predetermined_winner_not_participating(self, async_session: AsyncSession):
        """Тест завершения розыгрыша когда предопределенный победитель не участвует"""
        # Подготовка данных
        owner_id = 123456789
        channel_id = -1001234567890
        message_id = 127
        prize = "Приз когда подкрученный не участвует"
        winners_count = 2
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        predetermined_winner_id = 88888  # Победитель, который не будет участвовать
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Устанавливаем предопределенного победителя
        from database.requests.giveaway_repo import set_predetermined_winner
        await set_predetermined_winner(async_session, giveaway_id, predetermined_winner_id)
        
        # Создание участников (без предопределенного победителя)
        participants = []
        for i in range(5):
            user_id = 987654321 + i
            username = f"test_user{i}"
            
            # Создаем или обновляем пользователя
            user = await async_session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=f"Test{i}",
                    last_name=f"User{i}",
                    is_premium=False
                )
                async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=user_id,
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
            participants.append(user_id)
        
        await async_session.commit()
        
        # Обновляем розыгрыш в сессии после установки предопределенного победителя
        giveaway = await async_session.get(Giveaway, giveaway_id)
        
        # Тестируем выбор победителей
        selected_winners = select_winners(giveaway, participants)
        
        # Проверяем, что предопределенный победитель НЕ включен, так как не участвует
        assert predetermined_winner_id not in selected_winners
        assert len(selected_winners) == winners_count
        
        # Проверяем, что все победители из списка участников
        for winner_id in selected_winners:
            assert winner_id in participants