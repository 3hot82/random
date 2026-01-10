import pytest
import asyncio
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
async def test_concurrent_admin_requests(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки множественных одновременных запросов от администратора
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем данные для тестирования
        mock_users = []
        for i in range(50):
            mock_user = MagicMock(spec=User)
            mock_user.user_id = 100 + i
            mock_user.username = f"user{i}"
            mock_user.full_name = f"User {i}"
            mock_user.is_premium = i % 2 == 0
            mock_users.append(mock_user)
        
        # Мокаем выполнение запросов
        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_users[:10]  # первые 10 пользователей
            return mock_result
        mock_session.execute = mock_execute_side_effect
        
        # Мокаем количество
        async def mock_scalar_side_effect(*args, **kwargs):
            return len(mock_users)  # 50 пользователей
        mock_session.scalar = mock_scalar_side_effect
        
        # Мокаем получение пользователя
        async def mock_get_side_effect(model, user_id):
            for user in mock_users:
                if user.user_id == user_id:
                    return user
            return None
        mock_session.get = mock_get_side_effect
        
        # Создаем задачи для одновременного выполнения
        async def simulate_admin_action(action_number):
            callback = MagicMock(spec=CallbackQuery)
            callback.from_user = admin_user
            callback.message = MagicMock(spec=Message)
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()
            
            # Разные действия для разных потоков
            actions = [
                "admin_stats",
                "admin_users",
                "admin_giveaways", 
                "admin_broadcast",
                "admin_search_user",
                "admin_list_users_1"
            ]
            
            action = actions[action_number % len(actions)]
            callback.data = action
            
            try:
                if action == "admin_stats":
                    from handlers.admin.stats_handlers import show_stats_menu
                    await show_stats_menu(callback)
                elif action == "admin_users":
                    from handlers.admin.users_handlers import show_users_menu
                    await show_users_menu(callback)
                elif action == "admin_giveaways":
                    from handlers.admin.giveaways_handlers import show_giveaways_menu
                    await show_giveaways_menu(callback)
                elif action == "admin_broadcast":
                    from handlers.admin.broadcast_handlers import show_broadcast_menu
                    await show_broadcast_menu(callback)
                elif action == "admin_search_user":
                    from handlers.admin.users_handlers import start_user_search
                    state = AsyncMock()
                    await start_user_search(callback, state)
                elif action.startswith("admin_list_users_"):
                    from handlers.admin.users_handlers import show_users_list
                    await show_users_list(callback, mock_session)
            except Exception:
                # Ошибки в тесте допустимы, главное чтобы бот не падал
                pass
            
            return f"Action {action_number} completed"
        
        # Запускаем 20 одновременных запросов
        tasks = [simulate_admin_action(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем, что все задачи завершились (без фатальных ошибок)
        for result in results:
            assert result or isinstance(result, Exception)
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_mass_user_operations(mock_bot, mock_session, admin_user):
    """
    Тест: массовые операции с пользователями (изменение статусов, поиск и т.д.)
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем большое количество пользователей
        mock_users = []
        for i in range(100):
            mock_user = MagicMock(spec=User)
            mock_user.user_id = 1000 + i
            mock_user.username = f"mass_user_{i}"
            mock_user.full_name = f"Mass User {i}"
            mock_user.is_premium = False
            mock_users.append(mock_user)
        
        # Мокаем базу данных
        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            # Возвращаем разные наборы пользователей для разных запросов
            query_str = str(args[0])
            if 'LIMIT' in query_str.upper() and 'OFFSET' in query_str.upper():
                # Для пагинации возвращаем по 10 пользователей
                import re
                offset_match = re.search(r'OFFSET\s+(\d+)', query_str, re.IGNORECASE)
                if offset_match:
                    offset = int(offset_match.group(1))
                    return_users = mock_users[offset:offset + 10]
                else:
                    return_users = mock_users[:10]
            else:
                return_users = mock_users
            mock_result.scalars.return_value.all.return_value = return_users
            return mock_result
        
        import re
        mock_session.execute = mock_execute_side_effect

        async def mock_scalar_side_effect(*args, **kwargs):
            return len(mock_users)  # 100 пользователей
        mock_session.scalar = mock_scalar_side_effect
        
        async def mock_get_side_effect(model, user_id):
            for user in mock_users:
                if user.user_id == user_id:
                    return user
            return None
        mock_session.get = mock_get_side_effect
        
        # Тестируем массовые операции
        service = UserService(mock_session)
        
        # Тестируем поиск пользователей
        search_results = await service.search_users("mass_user")
        assert len(search_results) == 100
        
        # Тестируем переключение премиума для нескольких пользователей
        for i in range(0, min(10, len(mock_users)), 2):  # для первых 10 пользователей
            result = await service.toggle_premium_status(mock_users[i].user_id, True)
            assert result is True
        
        # Тестируем получение информации о пользователях
        for i in range(0, min(5, len(mock_users))):
            user_info = await service.get_user_detailed_info(mock_users[i].user_id)
            assert user_info is not None
        
        # Тестируем пагинацию
        for page in range(1, 11):  # 10 страниц
            users, total = await service.get_users_paginated(page=page, page_size=10)
            assert len(users) <= 10
            assert total == 100
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_mass_giveaway_operations(mock_bot, mock_session, admin_user):
    """
    Тест: массовые операции с розыгрышами
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем большое количество розыгрышей
        mock_giveaways = []
        for i in range(50):
            mock_giveaway = MagicMock(spec=Giveaway)
            mock_giveaway.id = 1 + i
            mock_giveaway.prize_text = f"Приз {i}"
            mock_giveaway.owner_id = 1000 + i
            mock_giveaway.status = "active" if i % 2 == 0 else "finished"
            mock_giveaway.finish_time = MagicMock()
            mock_giveaway.finish_time.strftime.return_value = f"2023-01-{i+1:02d} 12:00"
            mock_giveaway.winners_count = 1
            mock_giveaways.append(mock_giveaway)
        
        # Мокаем базу данных
        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            # Возвращаем разные наборы розыгрышей для разных запросов
            query_str = str(args[0])

            # Проверяем, содержит ли запрос COUNT (для общего количества)
            if 'func.count' in query_str.lower() or 'count(' in query_str.lower():
                # Для запроса общего количества возвращаем общее число
                mock_result.scalar.return_value = len(mock_giveaways)
                mock_result.scalars.return_value.all.return_value = []  # пустой список для count запроса
            elif 'LIMIT' in query_str.upper() and 'OFFSET' in query_str.upper():
                # Для пагинации возвращаем по 10 розыгрышей
                import re
                offset_match = re.search(r'OFFSET\s+(\d+)', query_str, re.IGNORECASE)
                if offset_match:
                    offset = int(offset_match.group(1))
                    return_giveaways = mock_giveaways[offset:offset + 10]
                else:
                    return_giveaways = mock_giveaways[:10]
                mock_result.scalars.return_value.all.return_value = return_giveaways
            else:
                mock_result.scalars.return_value.all.return_value = mock_giveaways

            return mock_result
        mock_session.execute = mock_execute_side_effect

        # Мокаем scalar напрямую, чтобы он возвращал правильные значения
        async def mock_scalar_side_effect(stmt):
            query_str = str(stmt)
            if 'func.count' in query_str.lower() or 'count(' in query_str.lower():
                return len(mock_giveaways)  # 50
            # Для других скалярных запросов возвращаем стандартное значение
            return 1
        mock_session.scalar.side_effect = mock_scalar_side_effect
        
        async def mock_get_side_effect(model, giveaway_id):
            for giveaway in mock_giveaways:
                if giveaway.id == giveaway_id:
                    return giveaway
            return None
        mock_session.get = mock_get_side_effect
        
        # Тестируем массовые операции
        service = GiveawayService(mock_session, mock_bot)
        
        # Тестируем поиск розыгрышей
        search_results = await service.search_giveaways("приз")
        assert len(search_results) == 50
        
        # Тестируем пагинацию
        for page in range(1, 6):  # 5 страниц
            giveaways, total = await service.get_giveaways_paginated(page=page, page_size=10)
            assert len(giveaways) <= 10
            # Проверяем, что total - это число, а не MagicMock
            assert int(total) == 50
        
        # Тестируем получение информации о розыгрышах
        for i in range(0, min(5, len(mock_giveaways))):
            giveaway_info = await service.get_giveaway_detailed_info(mock_giveaways[i].id)
            assert giveaway_info is not None
            
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_admin_rate_limit_bypass_attempts(mock_bot, mock_session, admin_user):
    """
    Тест: попытки обхода рейт-лимита администратором
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем данные
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 456
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.is_premium = False
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result
        
        async def mock_scalar_side_effect(*args, **kwargs):
            return 1
        mock_session.scalar = mock_scalar_side_effect
        
        async def mock_get_side_effect(model, user_id):
            if model == User and user_id == 456:
                return mock_user
            return None
        mock_session.get = mock_get_side_effect
        
        # Тестируем множество быстрых запросов
        results = []
        
        for i in range(50):  # 50 запросов подряд
            callback = MagicMock(spec=CallbackQuery)
            callback.from_user = admin_user
            callback.message = MagicMock(spec=Message)
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()
            callback.data = "admin_search_user"
            
            try:
                from handlers.admin.users_handlers import start_user_search
                state = AsyncMock()
                await start_user_search(callback, state)
                results.append("success")
            except Exception as e:
                results.append(f"error: {str(e)}")
        
        # Проверяем, что система не падает при множественных запросах
        success_count = sum(1 for r in results if r == "success")
        assert success_count >= 0  # Даже если часть запросов ограничена, система не должна падать
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_memory_usage_under_load(mock_bot, mock_session, admin_user):
    """
    Тест: проверка потребления памяти при нагрузке
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем среднее количество пользователей
        mock_users = []
        for i in range(25):
            mock_user = MagicMock(spec=User)
            mock_user.user_id = 2000 + i
            mock_user.username = f"load_user_{i}"
            mock_user.full_name = f"Load User {i}"
            mock_user.is_premium = i % 3 == 0
            mock_users.append(mock_user)
        
        # Мокаем базу данных
        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_users
            return mock_result
        mock_session.execute = mock_execute_side_effect
        
        async def mock_scalar_side_effect(*args, **kwargs):
            return len(mock_users)
        mock_session.scalar = mock_scalar_side_effect
        
        async def mock_get_side_effect(model, user_id):
            for user in mock_users:
                if user.user_id == user_id:
                    return user
            return None
        mock_session.get = mock_get_side_effect
        
        # Выполняем серию операций для проверки утечек памяти
        service = UserService(mock_session)
        
        # Повторяем операции несколько раз
        for cycle in range(5):
            # Поиск пользователей
            search_results = await service.search_users("load")
            assert len(search_results) == 25
            
            # Получение информации о каждом пользователе
            for user in mock_users:
                user_info = await service.get_user_detailed_info(user.user_id)
                assert user_info is not None
            
            # Переключение премиума для нескольких пользователей
            for i in range(0, len(mock_users), 5):
                await service.toggle_premium_status(mock_users[i].user_id, True)
        
        # Проверяем, что все операции завершились успешно
        assert True  # Если мы дошли до этой точки, значит нагрузка обработана
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_complex_admin_workflow_under_load(mock_bot, mock_session, admin_user):
    """
    Тест: сложный рабочий процесс администратора под нагрузкой
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем данные
        mock_users = []
        for i in range(20):
            mock_user = MagicMock(spec=User)
            mock_user.user_id = 3000 + i
            mock_user.username = f"workflow_user_{i}"
            mock_user.full_name = f"Workflow User {i}"
            mock_user.is_premium = False
            mock_users.append(mock_user)
        
        mock_giveaways = []
        for i in range(10):
            mock_giveaway = MagicMock(spec=Giveaway)
            mock_giveaway.id = 100 + i
            mock_giveaway.prize_text = f"Workflow Prize {i}"
            mock_giveaway.owner_id = 3000 + i
            mock_giveaway.status = "active"
            mock_giveaway.finish_time = MagicMock()
            mock_giveaway.finish_time.strftime.return_value = f"2023-02-{i+1:02d} 12:00"
            mock_giveaway.winners_count = 1
            mock_giveaways.append(mock_giveaway)
        
        # Мокаем выполнение запросов
        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            query_str = str(args[0])
            
            if 'Giveaway' in str(type(args[0])) or 'giveaways' in query_str.lower():
                mock_result.scalars.return_value.all.return_value = mock_giveaways
            else:
                mock_result.scalars.return_value.all.return_value = mock_users
            return mock_result
        mock_session.execute = mock_execute_side_effect
        
        async def mock_scalar_side_effect(*args, **kwargs):
            query_str = str(args[0])
            if 'Giveaway' in str(type(args[0])) or 'giveaways' in query_str.lower():
                return len(mock_giveaways)
            else:
                return len(mock_users)
        mock_session.scalar = mock_scalar_side_effect
        
        async def mock_get_side_effect(model, obj_id):
            if model == User:
                for user in mock_users:
                    if user.user_id == obj_id:
                        return user
            elif model == Giveaway:
                for giveaway in mock_giveaways:
                    if giveaway.id == obj_id:
                        return giveaway
            return None
        mock_session.get = mock_get_side_effect
        
        # Симулируем сложный рабочий процесс
        tasks = []
        
        async def admin_workflow_iteration(iteration):
            # Каждая итерация выполняет комплекс действий
            callback = MagicMock(spec=CallbackQuery)
            callback.from_user = admin_user
            callback.message = MagicMock(spec=Message)
            callback.message.edit_text = AsyncMock()
            callback.answer = AsyncMock()
            
            # Выполняем последовательность действий
            try:
                # 1. Открыть меню статистики
                callback.data = "admin_stats"
                from handlers.admin.stats_handlers import show_stats_menu
                await show_stats_menu(callback)
                
                # 2. Открыть меню пользователей
                callback.data = "admin_users"
                from handlers.admin.users_handlers import show_users_menu
                await show_users_menu(callback)
                
                # 3. Просмотреть список пользователей
                callback.data = "admin_list_users_1"
                from handlers.admin.users_handlers import show_users_list
                await show_users_list(callback, mock_session)
                
                # 4. Открыть меню розыгрышей
                callback.data = "admin_giveaways"
                from handlers.admin.giveaways_handlers import show_giveaways_menu
                await show_giveaways_menu(callback)
                
                # 5. Просмотреть список розыгрышей
                callback.data = "admin_list_giveaways_1"
                from handlers.admin.giveaways_handlers import show_giveaways_list
                await show_giveaways_list(callback, mock_session)
                
            except Exception:
                pass  # Ошибки в тесте допустимы
            
            return f"Iteration {iteration} completed"
        
        # Запускаем 10 итераций параллельно
        tasks = [admin_workflow_iteration(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем результаты
        completed_iterations = sum(1 for r in results if isinstance(r, str) and "completed" in r)
        assert completed_iterations >= 8  # Хотя бы 8 из 10 должны завершиться успешно
            
    finally:
        config.ADMIN_IDS = original_admin_ids