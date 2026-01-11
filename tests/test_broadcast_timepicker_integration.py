import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
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
from keyboards.admin_broadcast_time_keyboards import (
    get_broadcast_date_picker_keyboard,
    get_broadcast_time_picker_keyboard,
    get_manual_time_input_keyboard
)


class TestBroadcastTimePickerIntegration:
    """Интеграционные тесты для функций выбора времени рассылки"""

    @pytest.mark.asyncio
    async def test_full_schedule_broadcast_flow_with_date_picking(self):
        """Полный тест потока планирования рассылки с выбором даты и времени через кнопки"""
        
        # Создаем моки
        callback = AsyncMock(spec=CallbackQuery)
        callback.data = "admin_schedule_broadcast"
        callback.from_user = User(id=12345, is_bot=False, first_name="TestAdmin")
        callback.message = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            'broadcast_data': {
                'text': 'Test broadcast message',
                'photo': None,
                'video': None,
                'document': None
            }
        })
        state.clear = AsyncMock()
        
        session = AsyncMock(spec=AsyncSession)
        bot = AsyncMock()
        
        # 1. Начинаем планирование рассылки
        await start_schedule_broadcast(callback, state)
        
        # Проверяем, что состояние изменилось на ожидание выбора даты
        state.set_state.assert_called_with(BroadcastState.waiting_for_schedule_date)
        
        # 2. Выбираем дату (например, 25 декабря 2024 года)
        callback.data = "admin_broadcast_date_set:2024:12:25"
        callback.message.edit_text.reset_mock()  # Сбрасываем вызовы для проверки следующего шага
        state.set_state.reset_mock()
        
        await select_broadcast_date(callback, state)
        
        # Проверяем, что состояние изменилось на ожидание выбора времени
        state.set_state.assert_called_with(BroadcastState.waiting_for_schedule_time)
        
        # 3. Выбираем время (например, 15:30)
        callback.data = "admin_broadcast_time_set:2024:12:25:15:30"
        callback.message.edit_text.reset_mock()
        state.clear.reset_mock()
        
        # Мок для сервиса рассылки и планировщика
        with patch('handlers.admin.broadcast_handlers.BroadcastService') as mock_service_class, \
             patch('handlers.admin.broadcast_handlers.schedule_broadcast_task') as mock_schedule_task:
            
            # Создаем мок для экземпляра сервиса
            mock_service_instance = AsyncMock()
            mock_broadcast = MagicMock()
            mock_broadcast.id = 999
            mock_service_instance.create_broadcast.return_value = mock_broadcast
            mock_service_class.return_value = mock_service_instance
            
            await select_broadcast_time(callback, state, session, bot)
        
        # Проверяем, что рассылка была создана
        mock_service_instance.create_broadcast.assert_called_once()
        
        # Проверяем, что задача была запланирована
        mock_schedule_task.assert_called_once()
        
        # Проверяем, что состояние очищено
        state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_schedule_broadcast_flow_with_manual_input(self):
        """Полный тест потока планирования рассылки с ручным вводом времени"""
        
        # Создаем моки
        callback = AsyncMock(spec=CallbackQuery)
        callback.data = "admin_schedule_broadcast"
        callback.from_user = User(id=12345, is_bot=False, first_name="TestAdmin")
        callback.message = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        message = AsyncMock(spec=Message)
        message.text = "2024-12-25 15:30"
        message.from_user = User(id=12345, is_bot=False, first_name="TestAdmin")
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            'broadcast_data': {
                'text': 'Test broadcast message',
                'photo': None,
                'video': None,
                'document': None
            }
        })
        state.clear = AsyncMock()
        
        session = AsyncMock(spec=AsyncSession)
        bot = AsyncMock()
        
        # 1. Начинаем планирование рассылки
        await start_schedule_broadcast(callback, state)
        
        # 2. Переключаемся к ручному вводу времени
        callback.data = "admin_broadcast_manual_time"
        callback.message.edit_text.reset_mock()
        state.set_state.reset_mock()
        
        await switch_to_manual_time_input(callback, state)
        
        # Проверяем, что состояние изменилось на ожидание ручного ввода времени
        state.set_state.assert_called_with(BroadcastState.waiting_for_manual_schedule_time)
        
        # 3. Обрабатываем ручной ввод времени
        message.text = "2024-12-25 15:30"
        state.clear.reset_mock()
        
        with patch('handlers.admin.broadcast_handlers.BroadcastService') as mock_service_class, \
             patch('handlers.admin.broadcast_handlers.schedule_broadcast_task') as mock_schedule_task:
            
            mock_service_instance = AsyncMock()
            mock_broadcast = MagicMock()
            mock_broadcast.id = 999
            mock_service_instance.create_broadcast.return_value = mock_broadcast
            mock_service_class.return_value = mock_service_instance
            
            await process_manual_time_input(message, state, session, bot)
        
        # Проверяем, что рассылка была создана
        mock_service_instance.create_broadcast.assert_called_once()
        
        # Проверяем, что задача была запланирована
        mock_schedule_task.assert_called_once()
        
        # Проверяем, что состояние очищено
        state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyboard_generation_functions(self):
        """Тест генерации клавиатур для выбора времени"""
        
        # Тест генерации клавиатуры выбора даты
        keyboard = get_broadcast_date_picker_keyboard()
        assert keyboard is not None
        # Проверяем, что клавиатура содержит кнопки
        assert hasattr(keyboard, 'inline_keyboard')
        assert len(keyboard.inline_keyboard) > 0
        
        # Тест генерации клавиатуры выбора времени (для конкретной даты)
        keyboard = get_broadcast_time_picker_keyboard(2024, 12, 25)
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')
        assert len(keyboard.inline_keyboard) > 0
        
        # Тест генерации клавиатуры для ручного ввода
        keyboard = get_manual_time_input_keyboard()
        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')
        assert len(keyboard.inline_keyboard) > 0

    @pytest.mark.asyncio
    async def test_date_navigation_functionality(self):
        """Тест функциональности навигации по датам"""
        
        callback = AsyncMock(spec=CallbackQuery)
        callback.data = "admin_broadcast_cal_nav:2024:11"  # Навигация к ноябрю 2024
        callback.message = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Вызываем функцию навигации
        await navigate_broadcast_calendar(callback)
        
        # Проверяем, что сообщение было отредактировано
        callback.message.edit_text.assert_called_once()
        # Проверяем, что в тексте содержится информация о выборе даты
        args, kwargs = callback.message.edit_text.call_args
        assert "Выберите дату отправки" in args[0]

    @pytest.mark.asyncio
    async def test_validation_past_time_prevention(self):
        """Тест валидации, предотвращающей выбор времени в прошлом"""
        
        callback = AsyncMock(spec=CallbackQuery)
        # Пытаемся выбрать время в прошлом (например, 1 января 2020)
        callback.data = "admin_broadcast_time_set:2020:1:1:10:0"
        callback.answer = AsyncMock()
        callback.message = AsyncMock()
        callback.message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        session = AsyncMock(spec=AsyncSession)
        bot = AsyncMock()
        
        # Вызываем функцию выбора времени с прошедшим временем
        await select_broadcast_time(callback, state, session, bot)
        
        # Проверяем, что было показано предупреждение
        callback.answer.assert_called()
        # Проверяем, что аргументы содержат сообщение о прошедшем времени
        args, kwargs = callback.answer.call_args
        if 'show_alert' in kwargs:
            assert kwargs['show_alert'] is True
        if args:
            assert "Время уже прошло!" in str(args)

    @pytest.mark.asyncio
    async def test_invalid_time_format_handling(self):
        """Тест обработки неправильного формата времени при ручном вводе"""
        
        message = AsyncMock(spec=Message)
        message.text = "неправильный формат времени"
        message.from_user = User(id=12345, is_bot=False, first_name="TestAdmin")
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        session = AsyncMock(spec=AsyncSession)
        bot = AsyncMock()
        
        # Вызываем функцию обработки ручного ввода с неправильным форматом
        await process_manual_time_input(message, state, session, bot)
        
        # Проверяем, что было отправлено сообщение об ошибке
        message.answer.assert_called()
        # Проверяем, что последний вызов содержит сообщение об ошибке формата
        args, kwargs = message.answer.call_args
        assert "Неверный формат времени" in str(args[0]) if args else False