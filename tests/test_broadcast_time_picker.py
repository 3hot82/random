import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User, Chat
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.admin.broadcast_handlers import (
    start_schedule_broadcast,
    select_broadcast_date,
    navigate_broadcast_calendar,
    select_broadcast_time,
    switch_to_manual_time_input,
    process_manual_time_input,
    BroadcastState
)


@pytest.fixture
def mock_callback_query():
    callback = AsyncMock(spec=CallbackQuery)
    callback.data = "admin_schedule_broadcast"
    callback.from_user = User(id=12345, is_bot=False, first_name="Test")
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_message():
    message = AsyncMock(spec=Message)
    message.text = "Test message"
    message.from_user = User(id=12345, is_bot=False, first_name="Test")
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={'broadcast_data': {'text': 'Test broadcast'}})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    return bot


class TestBroadcastTimePicker:
    """Тесты для функций выбора времени рассылки"""

    async def test_start_schedule_broadcast(self, mock_callback_query, mock_state):
        """Тест начала планирования рассылки"""
        await start_schedule_broadcast(mock_callback_query, mock_state)
        
        # Проверяем, что состояние установлено правильно
        mock_state.set_state.assert_called_once_with(BroadcastState.waiting_for_schedule_date)
        
        # Проверяем, что сообщение отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        assert "Выберите дату отправки" in mock_callback_query.message.edit_text.call_args[0][0]
        
        # Проверяем, что ответ на callback отправлен
        mock_callback_query.answer.assert_called_once()

    async def test_select_broadcast_date(self, mock_callback_query, mock_state):
        """Тест выбора даты рассылки"""
        mock_callback_query.data = "admin_broadcast_date_set:2024:12:25"
        
        await select_broadcast_date(mock_callback_query, mock_state)
        
        # Проверяем, что состояние установлено правильно
        mock_state.set_state.assert_called_once_with(BroadcastState.waiting_for_schedule_time)
        
        # Проверяем, что сообщение отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        assert "25.12.2024" in mock_callback_query.message.edit_text.call_args[0][0]
        
        # Проверяем, что ответ на callback отправлен
        mock_callback_query.answer.assert_called_once()

    async def test_navigate_broadcast_calendar(self, mock_callback_query):
        """Тест навигации по календарю рассылки"""
        mock_callback_query.data = "admin_broadcast_cal_nav:2024:11"
        
        await navigate_broadcast_calendar(mock_callback_query)
        
        # Проверяем, что сообщение отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        assert "Выберите дату отправки" in mock_callback_query.message.edit_text.call_args[0][0]
        
        # Проверяем, что ответ на callback отправлен
        mock_callback_query.answer.assert_called_once()

    async def test_select_broadcast_time_success(self, mock_callback_query, mock_state, mock_session, mock_bot):
        """Тест успешного выбора времени рассылки"""
        mock_callback_query.data = "admin_broadcast_time_set:2024:12:25:15:30"
        
        from core.tools.broadcast_scheduler import schedule_broadcast_task
        from core.tools.broadcast_scheduler import schedule_broadcast_task
        # Мок для сервиса рассылки
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("handlers.admin.broadcast_handlers.BroadcastService", MagicMock())
            mp.setattr("core.tools.broadcast_scheduler.schedule_broadcast_task", AsyncMock())
            
            await select_broadcast_time(mock_callback_query, mock_state, mock_session, mock_bot)
        
        # Проверяем, что сообщение отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        # Проверяем, что последний вызов содержит информацию о запланированной рассылке
        args, kwargs = mock_callback_query.message.edit_text.call_args
        assert "запланирована на 2024-12-25 15:30" in args[0] if args else False
        
        # Проверяем, что состояние очищено
        mock_state.clear.assert_called_once()
        
        # Проверяем, что ответ на callback отправлен
        mock_callback_query.answer.assert_called_once()

    async def test_switch_to_manual_time_input(self, mock_callback_query, mock_state):
        """Тест переключения к ручному вводу времени"""
        await switch_to_manual_time_input(mock_callback_query, mock_state)
        
        # Проверяем, что состояние установлено правильно
        mock_state.set_state.assert_called_once_with(BroadcastState.waiting_for_manual_schedule_time)
        
        # Проверяем, что сообщение отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        assert "Введите время отправки в формате" in mock_callback_query.message.edit_text.call_args[0][0]
        
        # Проверяем, что ответ на callback отправлен
        mock_callback_query.answer.assert_called_once()

    async def test_process_manual_time_input_success(self, mock_message, mock_state, mock_session, mock_bot):
        """Тест успешной обработки ручного ввода времени"""
        mock_message.text = "2024-12-25 15:30"
        
        from core.tools.broadcast_scheduler import schedule_broadcast_task
        # Мок для сервиса рассылки
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("handlers.admin.broadcast_handlers.BroadcastService", MagicMock())
            mp.setattr("core.tools.broadcast_scheduler.schedule_broadcast_task", AsyncMock())
            
            await process_manual_time_input(mock_message, mock_state, mock_session, mock_bot)
        
        # Проверяем, что сообщение отправлено
        mock_message.answer.assert_called()
        # Проверяем, что последний вызов содержит информацию о запланированной рассылке
        args, kwargs = mock_message.answer.call_args
        assert "запланирована на 2024-12-25 15:30" in args[0] if args else False
        
        # Проверяем, что состояние очищено
        mock_state.clear.assert_called_once()

    async def test_process_manual_time_input_invalid_format(self, mock_message, mock_state):
        """Тест обработки неправильного формата времени"""
        mock_message.text = "invalid date format"
        
        await process_manual_time_input(mock_message, mock_state, AsyncMock(), AsyncMock())
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_message.answer.assert_called()
        # Проверяем, что последний вызов содержит сообщение об ошибке формата
        assert any("Неверный формат времени" in str(call) for call in mock_message.answer.call_args_list)

    async def test_process_manual_time_input_past_time(self, mock_message, mock_state):
        """Тест обработки времени в прошлом"""
        mock_message.text = "2020-01-01 10:00"  # Очевидно прошедшее время
        
        await process_manual_time_input(mock_message, mock_state, AsyncMock(), AsyncMock())
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_message.answer.assert_called()
        # Проверяем, что последний вызов содержит сообщение о том, что время в прошлом
        assert any("Время не может быть в прошлом" in str(call) for call in mock_message.answer.call_args_list)