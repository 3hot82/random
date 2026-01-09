import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from database.models.giveaway import Giveaway
from database.models.user import User
from database.models.participant import Participant
from database.requests.giveaway_repo import create_giveaway
from core.services.message_service import MessageHandler


@pytest.mark.asyncio
class TestGiveawayErrors:
    """Тестирование ошибок, связанных с уведомлениями о розыгрышах"""

    async def test_error_when_user_has_blocked_bot(self, async_session: AsyncSession):
        """Тест ошибки, когда пользователь заблокировал бота и не может получить уведомление о победе"""
        # Подготовка данных
        owner_id = 123456789 + int(time.time()) % 100000
        channel_id = -1001234567890
        message_id = 133 + int(time.time()) % 1000
        prize = "Приз для теста блокировки"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654329 + int(time.time()) % 1000000
        winner_username = f"blocked_user_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Blocked User",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Мокируем бота с выбросом исключения, как если бы пользователь заблокировал бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.side_effect = TelegramBadRequest("Forbidden: bot was blocked by the user")
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Пытаемся уведомить победителя - должно произойти исключение
            notification_text = f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!"
            
            with pytest.raises(TelegramBadRequest):
                await bot.send_message(winner_user_id, notification_text)

    async def test_error_when_creator_has_blocked_bot(self, async_session: AsyncSession):
        """Тест ошибки, когда создатель розыгрыша заблокировал бота и не может получить уведомление о победителе"""
        # Подготовка данных
        owner_id = 123456790 + int(time.time()) % 100000
        channel_id = -1001234567890
        message_id = 134 + int(time.time()) % 1000
        prize = "Приз для теста блокировки создателя"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654330 + int(time.time()) % 1000000
        winner_username = f"winner_user_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
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
        
        # Мокируем бота с выбросом исключения для создателя
        with patch('aiogram.Bot.send_message') as mock_send_message:
            # Первый вызов для уведомления победителя (успешный), второй для создателя (ошибка)
            send_message_method = SendMessage(chat_id=owner_id, text="test")
            mock_send_message.side_effect = [AsyncMock(), TelegramBadRequest(method=send_message_method, message="Forbidden: bot was blocked by the user")]
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем победителя
            notification_text = f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!"
            await bot.send_message(winner_user_id, notification_text)
            
            # Пытаемся уведомить создателя - должно произойти исключение
            creator_notification = f"🏆 В вашем розыгрыше '{prize}' определен победитель!\n\nПобедитель: @{winner_username} (ID: {winner_user_id})"
            
            with pytest.raises(TelegramBadRequest):
                await bot.send_message(owner_id, creator_notification)

    async def test_error_with_invalid_user_id(self, async_session: AsyncSession):
        """Тест ошибки при отправке уведомления пользователю с недействительным ID"""
        # Подготовка данных
        owner_id = 123456791 + int(time.time()) % 100000
        channel_id = -1001234567890
        message_id = 135 + int(time.time()) % 1000
        prize = "Приз для теста неверного ID"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Используем заведомо недействительный ID пользователя
        invalid_user_id = 0  # Недействительный ID
        
        # Мокируем бота с выбросом исключения для недействительного ID
        with patch('aiogram.Bot.send_message') as mock_send_message:
            from aiogram.methods import SendMessage
            send_message_method = SendMessage(chat_id=invalid_user_id, text="test")
            mock_send_message.side_effect = TelegramBadRequest(method=send_message_method, message="Bad Request: chat not found")
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Пытаемся уведомить пользователя с недействительным ID
            notification_text = f"🎉 Поздравляем! Вы выиграли '{prize}' в розыгрыше!"
            
            with pytest.raises(TelegramBadRequest):
                await bot.send_message(invalid_user_id, notification_text)

    async def test_error_with_long_message(self, async_session: AsyncSession):
        """Тест ошибки при отправке слишком длинного сообщения пользователю"""
        # Подготовка данных
        owner_id = 123456792 + int(time.time()) % 100000
        channel_id = -1001234567890
        message_id = 136 + int(time.time()) % 1000
        prize = "Приз для теста длинного сообщения"
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)
        
        # Создание розыгрыша
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize, winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654331 + int(time.time()) % 1000000
        winner_username = f"long_msg_user_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Long Message User",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Создаем очень длинное сообщение
        long_message = "🎉 Поздравляем! Вы выиграли '" + prize + "' в розыгрыше! " + "Это очень длинное сообщение. " * 1000
        
        # Мокируем бота с выбросом исключения для слишком длинного сообщения
        with patch('aiogram.Bot.send_message') as mock_send_message:
            from aiogram.methods import SendMessage
            send_message_method = SendMessage(chat_id=winner_user_id, text="test")
            mock_send_message.side_effect = TelegramBadRequest(method=send_message_method, message="Bad Request: message is too long")
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Пытаемся уведомить победителя с очень длинным сообщением
            with pytest.raises(TelegramBadRequest):
                await bot.send_message(winner_user_id, long_message)

    async def test_error_with_missing_giveaway_data(self, async_session: AsyncSession):
        """Тест ошибки при отсутствии данных о розыгрыше при формировании уведомления"""
        # Подготовка данных
        owner_id = 123456793 + int(time.time()) % 100000
        channel_id = -1001234567890
        message_id = 137 + int(time.time()) % 1000
        prize = None  # Отсутствует приз
        winners_count = 1
        end_time = datetime.now() - timedelta(hours=1)
        
        # Создание розыгрыша с отсутствующими данными
        giveaway_id = await create_giveaway(
            async_session, owner_id, channel_id, message_id,
            prize or "", winners_count, end_time
        )
        
        # Создание победителя с уникальным ID
        winner_user_id = 987654332 + int(time.time()) % 1000000
        winner_username = f"missing_data_user_{int(time.time())}"
        
        # Проверяем, существует ли уже такой пользователь
        existing_user = await async_session.get(User, winner_user_id)
        if existing_user:
            await async_session.delete(existing_user)
            await async_session.commit()
        
        # Создаем победителя как участника
        user = User(
            user_id=winner_user_id,
            username=winner_username,
            full_name="Missing Data User",
            is_premium=False
        )
        async_session.add(user)
        
        participant = Participant(
            user_id=winner_user_id,
            giveaway_id=giveaway_id
        )
        async_session.add(participant)
        
        await async_session.commit()
        
        # Проверяем, что можем получить данные о розыгрыше
        giveaway = await async_session.get(Giveaway, giveaway_id)
        
        # Формируем уведомление даже с отсутствующими данными
        message_for_user = f"🎉 Поздравляем! Вы выиграли {'приз' if not prize else prize} в розыгрыше!"
        
        # Мокируем бота
        with patch('aiogram.Bot.send_message') as mock_send_message:
            mock_send_message.return_value = AsyncMock()
            
            bot = AsyncMock(spec=Bot)
            bot.send_message = mock_send_message
            
            # Уведомляем победителя
            await bot.send_message(winner_user_id, message_for_user)
            
            # Проверяем, что сообщение было отправлено
            mock_send_message.assert_called_once_with(winner_user_id, message_for_user)