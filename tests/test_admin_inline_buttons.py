import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.storage.memory import MemoryStorage

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
async def test_admin_main_menu_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы основных кнопок главного меню админ-панели
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Тестируем каждую кнопку главного меню
        main_menu_callbacks = [
            "admin_stats",
            "admin_users",
            "admin_giveaways",
            "admin_broadcast"
        ]
        
        for callback_data in main_menu_callbacks:
            callback.data = callback_data
            
            # Проверяем, что не возникает исключений при обработке
            if callback_data == "admin_stats":
                from handlers.admin.stats_handlers import show_stats_menu
                await show_stats_menu(callback)
            elif callback_data == "admin_users":
                from handlers.admin.users_handlers import show_users_menu
                await show_users_menu(callback)
            elif callback_data == "admin_giveaways":
                from handlers.admin.giveaways_handlers import show_giveaways_menu
                await show_giveaways_menu(callback)
            elif callback_data == "admin_broadcast":
                from handlers.admin.broadcast_handlers import show_broadcast_menu
                await show_broadcast_menu(callback)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()  # Сбрасываем вызовы для следующего теста
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_stats_menu_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок меню статистики
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем данные для статистики
        side_effects = [100, 5, 50, 5]  # total_users, active_giveaways, total_participations, potential_bots
        current_call = 0
        
        async def mock_scalar_side_effect(*args, **kwargs):
            nonlocal current_call
            result = side_effects[current_call % len(side_effects)]
            current_call += 1
            return result
        
        mock_session.scalar = mock_scalar_side_effect
        
        # Тестируем каждую кнопку меню статистики
        stats_callbacks = [
            "admin_general_stats",
            "admin_user_growth",
            "admin_premium_stats",
            "admin_giveaway_stats",
            "admin_participation_stats"
        ]
        
        for callback_data in stats_callbacks:
            callback.data = callback_data
            
            if callback_data == "admin_general_stats":
                from handlers.admin.stats_handlers import show_general_stats
                await show_general_stats(callback, mock_session)
            elif callback_data == "admin_user_growth":
                from handlers.admin.stats_handlers import show_user_growth_stats
                await show_user_growth_stats(callback, mock_session)
            elif callback_data == "admin_premium_stats":
                from handlers.admin.stats_handlers import show_premium_stats
                await show_premium_stats(callback, mock_session)
            elif callback_data == "admin_giveaway_stats":
                from handlers.admin.stats_handlers import show_giveaway_stats
                await show_giveaway_stats(callback, mock_session)
            elif callback_data == "admin_participation_stats":
                from handlers.admin.stats_handlers import show_participation_stats
                await show_participation_stats(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_users_menu_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок меню пользователей
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем FSM state
        state = AsyncMock()
        
        # Мокаем данные пользователей
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 456
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.is_premium = False
        mock_user.created_at = MagicMock()
        mock_user.created_at.strftime.return_value = "2023-01-01 12:00"
        mock_user.premium_until = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        async def mock_execute_side_effect(*args, **kwargs):
            return mock_result
        mock_session.execute = mock_execute_side_effect
        
        # Мокаем количество участий
        async def mock_scalar_side_effect(*args, **kwargs):
            return 3
        mock_session.scalar = mock_scalar_side_effect
        
        # Мокаем получение пользователя
        async def mock_get_side_effect(model, user_id):
            if model == User and user_id == 456:
                return mock_user
            return None
        mock_session.get = mock_get_side_effect
        
        # Тестируем каждую кнопку меню пользователей
        users_callbacks = [
            "admin_search_user",
            "admin_list_users_1"
        ]
        
        for callback_data in users_callbacks:
            callback.data = callback_data
            
            if callback_data == "admin_search_user":
                from handlers.admin.users_handlers import start_user_search
                await start_user_search(callback, state)
            elif callback_data.startswith("admin_list_users_"):
                from handlers.admin.users_handlers import show_users_list
                await show_users_list(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_giveaways_menu_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок меню розыгрышей
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем FSM state
        state = AsyncMock()
        
        # Мокаем данные розыгрышей
        mock_giveaway = MagicMock(spec=Giveaway)
        mock_giveaway.id = 1
        mock_giveaway.prize_text = "Тестовый приз"
        mock_giveaway.owner_id = 456
        mock_giveaway.status = "active"
        mock_giveaway.finish_time = MagicMock()
        mock_giveaway.finish_time.strftime.return_value = "2023-01-10 12:00"
        mock_giveaway.winners_count = 1
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_giveaway]
        async def mock_execute_side_effect(*args, **kwargs):
            return mock_result
        mock_session.execute = mock_execute_side_effect
        
        # Мокаем количество участников
        async def mock_scalar_side_effect(*args, **kwargs):
            return 10
        mock_session.scalar = mock_scalar_side_effect
        
        # Мокаем получение розыгрыша
        async def mock_get_side_effect(model, giveaway_id):
            if model == Giveaway and giveaway_id == 1:
                return mock_giveaway
            return None
        mock_session.get = mock_get_side_effect
        
        # Тестируем каждую кнопку меню розыгрышей
        giveaways_callbacks = [
            "admin_search_giveaway",
            "admin_list_giveaways_1"
        ]
        
        for callback_data in giveaways_callbacks:
            callback.data = callback_data
            
            if callback_data == "admin_search_giveaway":
                from handlers.admin.giveaways_handlers import start_giveaway_search
                await start_giveaway_search(callback, state)
            elif callback_data.startswith("admin_list_giveaways_"):
                # Исправляем мок для возврата int вместо MagicMock
                original_scalar = mock_session.scalar
                async def fixed_scalar_side_effect(*args, **kwargs):
                    result = await original_scalar(*args, **kwargs) if hasattr(original_scalar, '__call__') else original_scalar
                    if isinstance(result, MagicMock):
                        return 10  # Возвращаем конкретное значение
                    return result
                mock_session.scalar = fixed_scalar_side_effect
                
                from handlers.admin.giveaways_handlers import show_giveaways_list
                await show_giveaways_list(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_broadcast_menu_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок меню рассылок
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем FSM state
        state = AsyncMock()
        
        # Мокаем рассылки для истории
        from database.models import Broadcast
        mock_broadcast = MagicMock(spec=Broadcast)
        mock_broadcast.id = 1
        mock_broadcast.created_at = MagicMock()
        mock_broadcast.created_at.strftime.return_value = "2023-01-01 12:00"
        mock_broadcast.message_text = "Тестовая рассылка"
        mock_broadcast.status = "sent"
        mock_broadcast.sent_count = 5
        mock_broadcast.total_count = 10
        mock_broadcast.failed_count = 0
        mock_broadcast.blocked_count = 0
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_broadcast]
        mock_session.execute.return_value = mock_result
        
        # Мокаем количество рассылок
        async def mock_scalar_side_effect(*args, **kwargs):
            return 1  # Одна рассылка
        mock_session.scalar = mock_scalar_side_effect
        
        # Тестируем каждую кнопку меню рассылок
        broadcast_callbacks = [
            "admin_create_broadcast",
            "admin_broadcast_history_1",
            "admin_scheduled_broadcasts_1"
        ]
        
        for callback_data in broadcast_callbacks:
            callback.data = callback_data
            
            if callback_data == "admin_create_broadcast":
                from handlers.admin.broadcast_handlers import start_create_broadcast
                await start_create_broadcast(callback, state)
            elif callback_data.startswith("admin_broadcast_history_"):
                from handlers.admin.broadcast_handlers import show_broadcast_history
                await show_broadcast_history(callback, mock_session)
            elif callback_data.startswith("admin_scheduled_broadcasts_"):
                from handlers.admin.broadcast_handlers import show_scheduled_broadcasts
                await show_scheduled_broadcasts(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_pagination_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок пагинации в меню администратора
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем данные для пагинации пользователей
        mock_users = []
        for i in range(25):  # Создаем 25 пользователей для теста пагинации
            mock_user = MagicMock(spec=User)
            mock_user.user_id = 100 + i
            mock_user.username = f"user{i}"
            mock_user.full_name = f"User {i}"
            mock_user.created_at = MagicMock()
            mock_user.created_at.strftime.return_value = f"2023-01-{i+1:02d} 12:00"
            mock_user.premium_until = None
            mock_users.append(mock_user)
        
        # Мокаем выполнение запроса для пагинации пользователей
        async def mock_execute_users_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            # Возвращаем только часть пользователей в зависимости от OFFSET и LIMIT
            query_str = str(args[0])
            offset = 0
            limit = 10
            
            if 'OFFSET' in query_str.upper():
                import re
                offset_match = re.search(r'OFFSET\s+(\d+)', query_str, re.IGNORECASE)
                if offset_match:
                    offset = int(offset_match.group(1))
            
            if 'LIMIT' in query_str.upper():
                import re
                limit_match = re.search(r'LIMIT\s+(\d+)', query_str, re.IGNORECASE)
                if limit_match:
                    limit = int(limit_match.group(1))
                    
            current_page_users = mock_users[offset:offset + limit]
            mock_result.scalars.return_value.all.return_value = current_page_users
            return mock_result
            
        # Мокаем данные розыгрышей для пагинации розыгрышей
        mock_giveaways = []
        for i in range(25):  # Создаем 25 розыгрышей для теста пагинации
            mock_giveaway = MagicMock(spec=Giveaway)
            mock_giveaway.id = i + 1
            mock_giveaway.prize_text = f"Приз {i+1}"
            mock_giveaway.owner_id = 100 + i
            mock_giveaway.status = "active"
            mock_giveaway.finish_time = MagicMock()
            mock_giveaway.finish_time.strftime.return_value = f"2023-01-{i+10:02d} 12:00"
            mock_giveaway.winners_count = 1
            mock_giveaways.append(mock_giveaway)
        
        # Мокаем выполнение запроса для пагинации розыгрышей
        async def mock_execute_giveaways_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            query_str = str(args[0])
            offset = 0
            limit = 10
            
            if 'OFFSET' in query_str.upper():
                import re
                offset_match = re.search(r'OFFSET\s+(\d+)', query_str, re.IGNORECASE)
                if offset_match:
                    offset = int(offset_match.group(1))
            
            if 'LIMIT' in query_str.upper():
                import re
                limit_match = re.search(r'LIMIT\s+(\d+)', query_str, re.IGNORECASE)
                if limit_match:
                    limit = int(limit_match.group(1))
                    
            current_page_giveaways = mock_giveaways[offset:offset + limit]
            mock_result.scalars.return_value.all.return_value = current_page_giveaways
            return mock_result
        
        # Мокируем Broadcast для пагинации рассылок
        from database.models import Broadcast
        mock_broadcasts = []
        for i in range(25):  # Создаем 25 рассылок для теста пагинации
            mock_broadcast = MagicMock(spec=Broadcast)
            mock_broadcast.id = i + 1
            mock_broadcast.created_at = MagicMock()
            mock_broadcast.created_at.strftime.return_value = f"2023-01-{i+1:02d} 12:00"
            mock_broadcast.message_text = f"Тестовая рассылка {i+1}"
            mock_broadcast.status = "sent"
            mock_broadcast.sent_count = 5
            mock_broadcast.total_count = 10
            mock_broadcast.failed_count = 0
            mock_broadcast.blocked_count = 0
            mock_broadcasts.append(mock_broadcast)
        
        # Мокаем выполнение запроса для пагинации рассылок
        async def mock_execute_broadcasts_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            query_str = str(args[0])
            offset = 0
            limit = 10
            
            if 'OFFSET' in query_str.upper():
                import re
                offset_match = re.search(r'OFFSET\s+(\d+)', query_str, re.IGNORECASE)
                if offset_match:
                    offset = int(offset_match.group(1))
            
            if 'LIMIT' in query_str.upper():
                import re
                limit_match = re.search(r'LIMIT\s+(\d+)', query_str, re.IGNORECASE)
                if limit_match:
                    limit = int(limit_match.group(1))
                    
            current_page_broadcasts = mock_broadcasts[offset:offset + limit]
            mock_result.scalars.return_value.all.return_value = current_page_broadcasts
            return mock_result
        
        # Мокаем запросы в зависимости от типа модели
        async def conditional_execute_side_effect(*args, **kwargs):
            query_str = str(args[0])
            if 'Giveaway' in str(query_str) or 'giveaways' in query_str.lower():
                return await mock_execute_giveaways_side_effect(*args, **kwargs)
            elif 'Broadcast' in str(query_str) or 'broadcasts' in query_str.lower():
                return await mock_execute_broadcasts_side_effect(*args, **kwargs)
            else:
                return await mock_execute_users_side_effect(*args, **kwargs)
        
        mock_session.execute = conditional_execute_side_effect
        
        # Мокаем общее количество - всегда возвращаем int для правильного сравнения
        async def mock_scalar_side_effect(*args, **kwargs):
            return 25  # Общее количество для всех типов данных
        mock_session.scalar = mock_scalar_side_effect
        
        # Тестируем кнопки пагинации
        pagination_callbacks = [
            "admin_list_users_1",
            "admin_list_users_2",
            "admin_list_giveaways_1",
            "admin_list_giveaways_2",
            "admin_broadcast_history_1",
            "admin_broadcast_history_2"
        ]
        
        for callback_data in pagination_callbacks:
            callback.data = callback_data
            
            # Импортируем и вызываем соответствующий обработчик
            if callback_data.startswith("admin_list_users_"):
                from handlers.admin.users_handlers import show_users_list
                await show_users_list(callback, mock_session)
            elif callback_data.startswith("admin_list_giveaways_"):
                from handlers.admin.giveaways_handlers import show_giveaways_list
                await show_giveaways_list(callback, mock_session)
            elif callback_data.startswith("admin_broadcast_history_"):
                from handlers.admin.broadcast_handlers import show_broadcast_history
                await show_broadcast_history(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_user_action_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок действий с конкретным пользователем
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем FSM state
        state = AsyncMock()
        
        # Мокаем конкретного пользователя
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 456
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.is_premium = False
        mock_user.created_at = MagicMock()
        mock_user.created_at.strftime.return_value = "2023-01-01 12:00"
        mock_user.premium_until = None
        
        # Мокаем получение пользователя
        async def mock_get_side_effect(model, user_id):
            if model == User and user_id == 456:
                return mock_user
            return None
        mock_session.get = mock_get_side_effect
        
        # Мокаем количество участий
        async def mock_scalar_side_effect(*args, **kwargs):
            return 3
        mock_session.scalar = mock_scalar_side_effect
        
        # Тестируем кнопки действий с пользователем
        user_action_callbacks = [
            ("admin_user_detail_456", "user_detail"),
            ("admin_grant_premium_456", "grant_premium"),
            ("admin_revoke_premium_456", "revoke_premium"),
            ("admin_confirm_premium_grant_456", "confirm_premium_grant"),
            ("admin_confirm_premium_revoke_456", "confirm_premium_revoke")
        ]
        
        for callback_data, action_type in user_action_callbacks:
            callback.data = callback_data
            
            # Извлекаем ID пользователя из callback_data
            parts = callback_data.split('_')
            user_id = int(parts[-1])  # ID всегда в последней части
            
            if action_type == "user_detail":
                from handlers.admin.users_handlers import show_user_detail
                await show_user_detail(callback, mock_session)
            elif action_type == "grant_premium":
                from handlers.admin.users_handlers import confirm_grant_premium
                await confirm_grant_premium(callback)
            elif action_type == "revoke_premium":
                from handlers.admin.users_handlers import confirm_revoke_premium
                await confirm_revoke_premium(callback)
            elif action_type == "confirm_premium_grant":
                from handlers.admin.users_handlers import process_premium_change
                await process_premium_change(callback, mock_session)
            elif action_type == "confirm_premium_revoke":
                from handlers.admin.users_handlers import process_premium_change
                await process_premium_change(callback, mock_session)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_giveaway_action_buttons(mock_bot, mock_session, admin_user):
    """
    Тест: проверка работы кнопок действий с конкретным розыгрышем
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = admin_user
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Мокаем FSM state
        state = AsyncMock()
        bot_mock = AsyncMock(spec=Bot)
        
        # Мокаем конкретный розыгрыш
        mock_giveaway = MagicMock(spec=Giveaway)
        mock_giveaway.id = 1
        mock_giveaway.prize_text = "Тестовый приз"
        mock_giveaway.owner_id = 456
        mock_giveaway.status = "active"
        mock_giveaway.finish_time = MagicMock()
        mock_giveaway.finish_time.strftime.return_value = "2023-01-10 12:00"
        mock_giveaway.winners_count = 1
        
        # Мокаем получение розыгрыша
        async def mock_get_side_effect(model, giveaway_id):
            if model == Giveaway and giveaway_id == 1:
                return mock_giveaway
            return None
        mock_session.get = mock_get_side_effect
        
        # Мокаем количество участников
        async def mock_scalar_side_effect(*args, **kwargs):
            return 10
        mock_session.scalar = mock_scalar_side_effect
        
        # Тестируем кнопки действий с розыгрышем
        giveaway_action_callbacks = [
            "admin_giveaway_detail_1",
            "admin_force_finish_1",
            "admin_confirm_giveaway_finish_1"
        ]
        
        for callback_data in giveaway_action_callbacks:
            # Правильная обработка callback данных
            if "confirm_giveaway_finish" in callback_data:
                parts = callback_data.split('_')
                giveaway_id = int(parts[-1])  # последняя часть - ID розыгрыша
                callback.data = f"admin_confirm_giveaway_finish_{giveaway_id}"
            else:
                callback.data = callback_data
            
            # Извлекаем ID розыгрыша из callback_data
            parts = callback_data.split('_')
            if len(parts) >= 3:
                giveaway_id = int(parts[-1])
                
                if "giveaway_detail" in callback_data:
                    # Добавляем нужные атрибуты для форматирования
                    mock_giveaway.created_at = MagicMock()
                    mock_giveaway.created_at.strftime.return_value = "2023-01-01 12:00"
                    
                    from handlers.admin.giveaways_handlers import show_giveaway_detail
                    await show_giveaway_detail(callback, mock_session)
                elif "force_finish" in callback_data:
                    from handlers.admin.giveaways_handlers import confirm_force_finish_giveaway
                    await confirm_force_finish_giveaway(callback)
                elif "confirm_giveaway_finish" in callback.data:
                    # Для этого обработчика также нужен объект бота
                    from handlers.admin.giveaways_handlers import process_giveaway_action
                    await process_giveaway_action(callback, mock_session, bot_mock)
            
            # Проверяем, что метод edit_text был вызван
            callback.message.edit_text.assert_called()
            callback.message.edit_text.reset_mock()
            
    finally:
        config.ADMIN_IDS = original_admin_ids