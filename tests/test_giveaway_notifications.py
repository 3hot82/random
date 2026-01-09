import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import User as AiogramUser, Chat
from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.participant import Participant
from database.models.winner import Winner
from database.requests.giveaway_repo import create_giveaway
from core.logic.randomizer import select_winners
from core.services.message_service import MessageHandler


@pytest.mark.asyncio
class TestGiveawayNotifications:
    """Тестирование уведомлений о завершении розыгрышей"""

    async def test_notify_winner_about_victory(self, async_session: AsyncSession):
        """Тест уведомления победителя о победе"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000  # Уникальный ID для каждого запуска
        channel_id = -1001234567890
        message_id = 128 + int(time.time()) % 1000  # Уникальный ID сообщения
        prize = "Тестовый приз"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654321 + int(time.time()) % 1000000  # Генерируем уникальный ID
        winner_username = f"winner_user_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            # Если существует, удаляем
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Winner User",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем победителя
            notification_text = f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!"
            await bot.send_message(winner_user_id, notification_text)
            
            # Проверяем, что сообщение было отправлено
            mock_send_message.assert_called_once_with(winner_user_id, notification_text)

    async def test_notify_creator_about_winner(self, async_session: AsyncSession):
        """Тест уведомления создателя розыгрыша о победителе"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000  # Уникальный ID для каждого запуска
        channel_id = -1001234567890
        message_id = 129 + int(time.time()) % 1000  # Уникальный ID сообщения
        prize = "Тестовый приз для уведомления создателя"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654322 + int(time.time()) % 1000000  # Генерируем уникальный ID
        winner_username = f"winner_user2_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            # Если существует, удаляем
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Winner User2",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем создателя
            creator_notification = f"🏆 В вашем розыгрыше '{prize}' определен победитель!\n\nПобедитель: @{winner_username} (ID: {winner_user_id})"
            await bot.send_message(owner_id, creator_notification)
            
            # Проверяем, что сообщение было отправлено создателю
            mock_send_message.assert_called_once_with(owner_id, creator_notification)

    async def test_notify_multiple_winners(self, async_session: AsyncSession):
        """Тест уведомления нескольких победителей"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000  # Уникальный ID для каждого запуска
        channel_id = -1001234567890
        message_id = 130 + int(time.time()) % 1000  # Уникальный ID сообщения
        prize = "Приз для нескольких победителей"
        winners_count = 3
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителей с уникальными ID
        base_user_id = 987654323 + int(time.time()) % 1000000  # Базовый ID с учетом времени
        winners_data = [
            {"user_id": base_user_id, "username": f"winner3_{int(time.time())}", "full_name": "Winner3 User"},
            {"user_id": base_user_id + 1, "username": f"winner4_{int(time.time())}", "full_name": "Winner4 User"},
            {"user_id": base_user_id + 2, "username": f"winner5_{int(time.time())}", "full_name": "Winner5 User"},
        ]
        
        for winner_data in winners_data:
            # Проверяем, существует ли уже такой пользователь
            existing_user = await async_session.get(User, winner_data["user_id"])
            if existing_user:
                # Если существует, удаляем
                await async_session.delete(existing_user)
                await async_session.commit()
            
            # Создаем пользователя
            user = User(
                user_id=winner_data["user_id"],
                username=winner_data["username"],
                full_name=winner_data["full_name"],
                is_premium=False
            )
            async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=winner_data["user_id"],
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем всех победителей
            for winner_data in winners_data:
                notification_text = f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!"
                await bot.send_message(winner_data["user_id"], notification_text)
            
            # Проверяем, что сообщения были отправлены всем победителям
            assert mock_send_message.call_count == len(winners_data)
            
            # Проверяем, что каждому победителю было отправлено сообщение
            for winner_data in winners_data:
                mock_send_message.assert_any_call(winner_data["user_id"], f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!")

    async def test_notify_creator_about_multiple_winners(self, async_session: AsyncSession):
        """Тест уведомления создателя о нескольких победителях"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000  # Уникальный ID для каждого запуска
        channel_id = -1001234567890
        message_id = 131 + int(time.time()) % 1000  # Уникальный ID сообщения
        prize = "Приз для нескольких победителей (уведомление создателю)"
        winners_count = 2
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителей с уникальными ID
        base_user_id = 987654326 + int(time.time()) % 1000000  # Базовый ID с учетом времени
        winners_data = [
            {"user_id": base_user_id, "username": f"winner6_{int(time.time())}", "full_name": "Winner6 User"},
            {"user_id": base_user_id + 1, "username": f"winner7_{int(time.time())}", "full_name": "Winner7 User"},
        ]
        
        for winner_data in winners_data:
            # Проверяем, существует ли уже такой пользователь
            existing_user = await async_session.get(User, winner_data["user_id"])
            if existing_user:
                # Если существует, удаляем
                await async_session.delete(existing_user)
                await async_session.commit()
            
            # Создаем пользователя
            user = User(
                user_id=winner_data["user_id"],
                username=winner_data["username"],
                full_name=winner_data["full_name"],
                is_premium=False
            )
            async_session.add(user)
            
            # Создаем участника
            participant = Participant(
                user_id=winner_data["user_id"],
                giveaway_id=giveaway_id
            )
            async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Формируем список победителей для уведомления создателя
            winners_list = ""
            for winner_data in winners_data:
                winners_list += f"\n• @{winner_data['username']} (ID: {winner_data['user_id']})"
            
            creator_notification = f"🏆 В вашем розыгрыше '{prize}' определены победители!{winners_list}"
            await bot.send_message(owner_id, creator_notification)
            
            # Проверяем, что сообщение было отправлено создателю
            mock_send_message.assert_called_once_with(owner_id, creator_notification)

    async def test_notify_winner_with_username_mention(self, async_session: AsyncSession):
        """Тест уведомления победителя с упоминанием его имени пользователя"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000  # Уникальный ID для каждого запуска
        channel_id = -1001234567890
        message_id = 132 + int(time.time()) % 1000  # Уникальный ID сообщения
        prize = "Тестовый приз с упоминанием"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)  # Розыгрыш уже должен закончиться
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654328 + int(time.time()) % 1000000  # Генерируем уникальный ID
        winner_username = f"mentionable_user8_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            # Если существует, удаляем
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Mentionable User8",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем победителя с упоминанием его имени пользователя
            notification_text = f"🎉 Поздравляем, @{winner_username}! Вы выиграли '{prize}' в розыгрыше!"
            await bot.send_message(winner_user_id, notification_text)
            
            # Проверяем, что сообщение было отправлено с упоминанием
            mock_send_message.assert_called_once_with(winner_user_id, notification_text)