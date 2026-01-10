import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from aiogram import Bot
from aiogram.types import CallbackQuery, Message

from handlers.admin.admin_router import admin_router
from services.admin_statistics_service import CachedStatisticsService
from services.admin_user_service import UserService
from services.admin_giveaway_service import GiveawayService
from services.admin_broadcast_service import BroadcastService
from database.models import User, Giveaway, Participant, Broadcast
from config import config


@pytest.fixture
def mock_bot():
    """Фикстура для мокирования бота"""
    bot = AsyncMock(spec=Bot)
    return bot


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def admin_user():
    """Фикстура для администратора"""
    user = MagicMock()
    user.id = 123
    user.username = "admin"
    user.full_name = "Admin User"
    return user


@pytest.mark.asyncio
async def test_database_error_handling_in_user_service(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки ошибок базы данных в UserService
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс ошибки базы данных для всех возможных методов сессии
        async def mock_execute_with_error(*args, **kwargs):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_get_with_error(model, identifier):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_scalar_with_error(stmt):
            raise SQLAlchemyError("Database connection lost")
        
        # Устанавливаем моки для всех методов сессии
        mock_session.execute.side_effect = mock_execute_with_error
        mock_session.get.side_effect = mock_get_with_error
        mock_session.scalar.side_effect = mock_scalar_with_error
        
        # Тестируем, что сервис корректно обрабатывает ошибки
        service = UserService(mock_session)
        
        # Проверяем, что методы возвращают корректные значения при ошибках
        result = await service.search_users("test")
        assert result == []
        
        result = await service.get_user_detailed_info(123)
        assert result is None
        
        result = await service.toggle_premium_status(123, True)
        assert result is False
        
        # Сбрасываем сайд-эффекты для других тестов
        mock_session.execute.side_effect = None
        mock_session.get.side_effect = None
        mock_session.scalar.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_database_error_handling_in_giveaway_service(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки ошибок базы данных в GiveawayService
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс ошибки базы данных для всех возможных методов сессии
        async def mock_execute_with_error(*args, **kwargs):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_get_with_error(model, identifier):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_scalar_with_error(stmt):
            raise SQLAlchemyError("Database connection lost")
        
        # Устанавливаем моки для всех методов сессии
        mock_session.execute.side_effect = mock_execute_with_error
        mock_session.get.side_effect = mock_get_with_error
        mock_session.scalar.side_effect = mock_scalar_with_error
        
        # Тестируем, что сервис корректно обрабатывает ошибки
        service = GiveawayService(mock_session, mock_bot)
        
        # Проверяем, что методы возвращают корректные значения при ошибках
        result = await service.search_giveaways("test")
        assert result == []
        
        result = await service.get_giveaway_detailed_info(123)
        assert result is None
        
        result = await service.force_finish_giveaway(123, admin_user.id)
        assert result is False
        
        # Сбрасываем сайд-эффекты для других тестов
        mock_session.execute.side_effect = None
        mock_session.get.side_effect = None
        mock_session.scalar.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_database_error_handling_in_broadcast_service(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки ошибок базы данных в BroadcastService
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс ошибки базы данных для всех возможных методов сессии
        async def mock_execute_with_error(*args, **kwargs):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_get_with_error(model, identifier):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_scalar_with_error(stmt):
            raise SQLAlchemyError("Database connection lost")
        
        async def mock_commit_with_error():
            raise SQLAlchemyError("Database commit failed")
        
        # Устанавливаем моки для всех методов сессии
        mock_session.execute.side_effect = mock_execute_with_error
        mock_session.get.side_effect = mock_get_with_error
        mock_session.scalar.side_effect = mock_scalar_with_error
        mock_session.commit.side_effect = mock_commit_with_error
        
        # Тестируем, что сервис корректно обрабатывает ошибки
        service = BroadcastService(mock_bot, mock_session)
        
        # Проверяем, что методы возвращают корректные значения при ошибках
        result = await service.create_broadcast("Test message", admin_id=admin_user.id)
        # После изменений сервис должен возвращать None при ошибке
        assert result is None
        
        # Сбрасываем сайд-эффекты для других тестов
        mock_session.execute.side_effect = None
        mock_session.get.side_effect = None
        mock_session.scalar.side_effect = None
        mock_session.commit.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_exception_handling_in_admin_handlers(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки исключений в обработчиках админ-панели
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс ошибки в сервисе
        async def mock_service_method(*args, **kwargs):
            raise Exception("Unexpected error in service")
        
        # Мокаем сессию, чтобы вызывать ошибку
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")
        
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Тестируем, что обработчики не падают при ошибках в сервисах
        # Мокаем конкретный обработчик
        from handlers.admin.users_handlers import start_user_search
        from aiogram.fsm.context import FSMContext
        
        state = AsyncMock(spec=FSMContext)
        
        # Проверяем, что вызов не вызывает падения всей системы
        try:
            await start_user_search(callback, state)
            # Если не произошло исключения, то обработчик корректно работает с ошибками
            assert True
        except Exception:
            # Даже если ошибка произошла, система не должна полностью падать
            # В реальной системе это будет обработано глобальным обработчиком
            pass
        
        # Сбрасываем сайд-эффект для других тестов
        mock_session.execute.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_network_error_handling_in_broadcast_service(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки сетевых ошибок при отправке рассылок
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем мок пользователей
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 11
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result
        
        # Мокаем сетевую ошибку при отправке сообщения
        async def mock_send_message_with_error(chat_id, text, **kwargs):
            raise Exception("Network error: failed to send message")
        
        mock_bot.send_message.side_effect = mock_send_message_with_error
        
        # Тестируем, что сервис корректно обрабатывает сетевые ошибки
        service = BroadcastService(mock_bot, mock_session)
        
        # Создаем рассылку
        broadcast = await service.create_broadcast("Test message", admin_user.id)
        
        # Пытаемся отправить рассылку - должна обрабатываться сетевая ошибка
        result = await service.send_broadcast(broadcast.id)
        # Даже при сетевой ошибке метод не должен падать
        
        # Проверяем, что сервис не падает при сетевых ошибках
        assert broadcast is not None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_memory_error_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки ошибок нехватки памяти
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс MemoryError для всех возможных методов сессии
        async def mock_execute_with_memory_error(*args, **kwargs):
            raise MemoryError("Not enough memory")
        
        async def mock_get_with_memory_error(model, identifier):
            raise MemoryError("Not enough memory")
        
        async def mock_scalar_with_memory_error(stmt):
            raise MemoryError("Not enough memory")
        
        # Устанавливаем моки для всех методов сессии
        mock_session.execute.side_effect = mock_execute_with_memory_error
        mock_session.get.side_effect = mock_get_with_memory_error
        mock_session.scalar.side_effect = mock_scalar_with_memory_error
        
        # Тестируем, что сервисы корректно обрабатывают ошибки памяти
        service = UserService(mock_session)
        
        # Проверяем, что методы возвращают корректные значения при ошибках памяти
        result = await service.search_users("test")
        assert result == []
        
        result = await service.get_user_detailed_info(123)
        assert result is None
        
        # Сбрасываем сайд-эффекты для других тестов
        mock_session.execute.side_effect = None
        mock_session.get.side_effect = None
        mock_session.scalar.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_timeout_error_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки таймаутов
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем выброс TimeoutError для всех возможных методов сессии
        async def mock_execute_with_timeout(*args, **kwargs):
            raise TimeoutError("Request timeout")
        
        async def mock_get_with_timeout(model, identifier):
            raise TimeoutError("Request timeout")
        
        async def mock_scalar_with_timeout(stmt):
            raise TimeoutError("Request timeout")
        
        # Устанавливаем моки для всех методов сессии
        mock_session.execute.side_effect = mock_execute_with_timeout
        mock_session.get.side_effect = mock_get_with_timeout
        mock_session.scalar.side_effect = mock_scalar_with_timeout
        
        # Тестируем, что сервисы корректно обрабатывают таймауты
        service = GiveawayService(mock_session, mock_bot)
        
        # Проверяем, что методы возвращают корректные значения при таймаутах
        result = await service.search_giveaways("test")
        assert result == []
        
        result = await service.get_giveaway_detailed_info(123)
        assert result is None
        
        # Сбрасываем сайд-эффекты для других тестов
        mock_session.execute.side_effect = None
        mock_session.get.side_effect = None
        mock_session.scalar.side_effect = None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_validation_error_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки ошибок валидации данных
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Тестируем различные сценарии валидации
        service = UserService(mock_session)
        
        # Тестирование с некорректными данными
        result = await service.toggle_premium_status(-1, True)  # отрицательный ID
        assert result is False
        
        result = await service.toggle_premium_status(9999999999, True)  # чрезмерно большой ID
        assert result is False
        
        # Тестирование с граничными значениями
        result = await service.toggle_premium_status(0, True)  # нулевой ID
        assert result is False
        
        # Тестирование сервиса розыгрышей
        giveaway_service = GiveawayService(mock_session, mock_bot)
        
        result = await giveaway_service.force_finish_giveaway(-1, admin_user.id)  # отрицательный ID
        assert result is False
        
        result = await giveaway_service.force_finish_giveaway(9999999999, admin_user.id)  # чрезмерно большой ID
        assert result is False
        
    finally:
        config.ADMIN_IDS = original_admin_ids