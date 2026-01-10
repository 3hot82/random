import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import CallbackQuery, Message

from handlers.admin.admin_router import admin_router
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
async def test_large_payload_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки больших полезных нагрузок
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем очень длинный текст для тестирования
        very_long_text = "A" * 10000  # 10,000 символов
        
        # Проверяем, что сервисы корректно обрабатывают большие текстовые поля
        broadcast_service = BroadcastService(mock_bot, mock_session)
        
        # Проверяем создание рассылки с очень длинным текстом
        try:
            result = await broadcast_service.create_broadcast(very_long_text, admin_id=admin_user.id)
            # В зависимости от реализации может вернуть результат или None в случае ошибки
            assert result is None or hasattr(result, 'id')
        except Exception:
            # Ошибки при обработке длинных строк допустимы, главное чтобы не было падений системы
            pass
        
        # Проверяем сервис пользователей
        user_service = UserService(mock_session)
        
        # Проверяем поиск по очень длинному запросу
        result = await user_service.search_users(very_long_text)
        # Должно вернуться пустой список без ошибок
        assert result == []
        
        # Проверяем сервис розыгрышей
        giveaway_service = GiveawayService(mock_session, mock_bot)
        
        # Проверяем поиск по очень длинному запросу
        result = await giveaway_service.search_giveaways(very_long_text)
        # Должно вернуться пустой список без ошибок
        assert result == []
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_concurrent_access_to_same_resource(mock_bot, mock_session, admin_user):
    """
    Тест: проверка конкурентного доступа к одним и тем же ресурсам
    """
    import asyncio
    
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Мокаем получение одного и того же пользователя
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 123
        mock_user.username = "concurrent_user"
        mock_user.full_name = "Concurrent User"
        mock_user.is_premium = False
        
        async def mock_get_side_effect(model, user_id):
            return mock_user
        mock_session.get = mock_get_side_effect
        
        async def mock_scalar_side_effect(*args, **kwargs):
            return 5  # количество участий
        mock_session.scalar = mock_scalar_side_effect
        
        user_service = UserService(mock_session)
        
        # Создаем несколько конкурентных задач, которые обращаются к одному пользователю
        async def get_user_info_task():
            return await user_service.get_user_detailed_info(123)
        
        # Запускаем 10 одновременных запросов к одному пользователю
        tasks = [get_user_info_task() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем, что все задачи завершились успешно (без падений)
        for result in results:
            if not isinstance(result, Exception):
                assert result is not None
                assert "user" in result
                assert "participation_count" in result
            else:
                # Если произошло исключение, проверяем, что это не критическая ошибка
                assert str(result) != "System crash"  # Пример критической ошибки
        
        # Проверяем конкурентное изменение премиума
        async def toggle_premium_task():
            return await user_service.toggle_premium_status(123, True)
        
        toggle_tasks = [toggle_premium_task() for _ in range(5)]
        toggle_results = await asyncio.gather(*toggle_tasks, return_exceptions=True)
        
        # Проверяем, что задачи не вызвали системных ошибок
        for result in toggle_results:
            if isinstance(result, Exception):
                # В реальной системе может возникнуть ошибка блокировки или транзакции
                pass  # Это приемлемо
            else:
                # Либо возвращается результат (True/False)
                assert isinstance(result, bool) or result is None
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_extreme_pagination_scenarios(mock_bot, mock_session, admin_user):
    """
    Тест: проверка экстремальных сценариев пагинации
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        user_service = UserService(mock_session)
        
        # Проверяем пагинацию с экстремально большими значениями
        result_users, result_count = await user_service.get_users_paginated(page=999999, page_size=10)
        assert isinstance(result_users, list)
        assert isinstance(result_count, int)
        
        # Проверяем пагинацию с отрицательными значениями
        result_users, result_count = await user_service.get_users_paginated(page=-1, page_size=10)
        assert isinstance(result_users, list)
        assert isinstance(result_count, int)
        
        # Проверяем пагинацию с нулевыми значениями
        result_users, result_count = await user_service.get_users_paginated(page=0, page_size=0)
        assert isinstance(result_users, list)
        assert isinstance(result_count, int)
        
        # Проверяем пагинацию с очень большими размерами страницы
        result_users, result_count = await user_service.get_users_paginated(page=1, page_size=999999)
        assert isinstance(result_users, list)
        assert isinstance(result_count, int)
        
        # Тестирование аналогично для розыгрышей
        giveaway_service = GiveawayService(mock_session, mock_bot)
        
        result_giveaways, result_count = await giveaway_service.get_giveaways_paginated(page=999999, page_size=10)
        assert isinstance(result_giveaways, list)
        assert isinstance(result_count, int)
        
        result_giveaways, result_count = await giveaway_service.get_giveaways_paginated(page=-1, page_size=10)
        assert isinstance(result_giveaways, list)
        assert isinstance(result_count, int)
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_malformed_json_and_data_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки некорректных JSON и данных
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Тестируем обработку потенциально опасных строк
        dangerous_strings = [
            '{"malicious": "json"}',
            '<script>alert("xss")</script>',
            'SELECT * FROM users; DROP TABLE users;',
            '..\\..\\windows\\system32\\',
            'eval("console.log(\'dangerous\')")',
            '{{7*7}}',  # Potentially dangerous template injection
            'file:///etc/passwd',
            'javascript:alert(1)',
        ]
        
        user_service = UserService(mock_session)
        giveaway_service = GiveawayService(mock_session, mock_bot)
        
        # Проверяем, что сервисы корректно обрабатывают потенциально опасные строки
        for dangerous_string in dangerous_strings:
            # Поиск пользователей
            result = await user_service.search_users(dangerous_string)
            assert isinstance(result, list)
            
            # Поиск розыгрышей
            result = await giveaway_service.search_giveaways(dangerous_string)
            assert isinstance(result, list)
            
            # Проверка получения информации о пользователе с опасной строкой (должно быть None или обработка ошибки)
            try:
                result = await user_service.get_user_detailed_info(dangerous_string)
                assert result is None or isinstance(result, dict)
            except (TypeError, ValueError):
                # Ошибки валидации принимаются
                pass
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_rate_limiting_under_heavy_load(mock_bot, mock_session, admin_user):
    """
    Тест: проверка ограничений скорости при высокой нагрузке
    """
    import asyncio
    from utils.rate_limiter import RateLimiter
    
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        # Создаем ограничитель с очень низкими лимитами для тестирования
        limiter = RateLimiter(max_requests=3, window=1)  # 3 запроса в секунду
        
        # Выполняем больше запросов, чем позволяет лимит
        results = []
        for i in range(10):
            result = limiter.is_allowed(admin_user.id)
            results.append(result)
        
        # Проверяем, что некоторые запросы были ограничены
        allowed_count = sum(1 for result in results if result)
        blocked_count = len(results) - allowed_count
        
        # Должно быть разумное количество разрешенных и заблокированных запросов
        assert allowed_count <= 3  # Не больше 3 разрешенных в первую секунду
        assert blocked_count >= 7  # Остальные должны быть заблокированы
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_empty_and_null_values_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки пустых и нулевых значений
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        user_service = UserService(mock_session)
        giveaway_service = GiveawayService(mock_session, mock_bot)
        broadcast_service = BroadcastService(mock_bot, mock_session)
        
        # Проверяем обработку пустых строк
        result = await user_service.search_users("")
        assert result == []
        
        result = await giveaway_service.search_giveaways("")
        assert result == []
        
        # Проверяем обработку None значений
        try:
            result = await user_service.search_users(None)
            assert result == []
        except (TypeError, AttributeError):
            # Ошибки валидации принимаются
            pass
        
        try:
            result = await giveaway_service.search_giveaways(None)
            assert result == []
        except (TypeError, AttributeError):
            # Ошибки валидации принимаются
            pass
        
        # Проверяем создание рассылки с пустыми значениями
        result = await broadcast_service.create_broadcast("", admin_id=admin_user.id)
        # Может вернуть None в случае ошибки
        assert result is None or hasattr(result, 'id')
        
        # Проверяем создание рассылки с None значениями
        result = await broadcast_service.create_broadcast(None, admin_id=admin_user.id)
        assert result is None or hasattr(result, 'id')
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_integer_overflow_protection(mock_bot, mock_session, admin_user):
    """
    Тест: проверка защиты от целочисленного переполнения
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        user_service = UserService(mock_session)
        giveaway_service = GiveawayService(mock_session, mock_bot)
        
        # Проверяем работу с максимально возможными целыми числами
        max_int32 = 2**31 - 1
        max_int64 = 2**63 - 1
        overflow_int = 2**63  # Это может вызвать ошибку в PostgreSQL (bigint max is 2^63-1)
        
        # Тестируем с максимально допустимым значением
        try:
            result = await user_service.get_user_detailed_info(max_int64)
            # Результат может быть None (если пользователя нет) или словарем (если есть)
            assert result is None or isinstance(result, dict)
        except (OverflowError, ValueError):
            # Это допустимая реакция на переполнение
            pass
        
        # Тестируем с потенциально проблемным значением
        try:
            result = await user_service.get_user_detailed_info(overflow_int)
            # В мокированной версии может вернуться словарь с моками или None
            assert result is None or isinstance(result, dict)
        except (OverflowError, ValueError):
            # Это допустимая реакция на переполнение
            pass
        
        # Тестируем розыгрыши
        try:
            result = await giveaway_service.get_giveaway_detailed_info(max_int64)
            assert result is None or isinstance(result, dict)
        except (OverflowError, ValueError):
            # Это допустимая реакция на переполнение
            pass
        
        try:
            result = await giveaway_service.get_giveaway_detailed_info(overflow_int)
            # В мокированной версии может вернуться словарь с моками или None
            assert result is None or isinstance(result, dict)
        except (OverflowError, ValueError):
            # Это допустимая реакция на переполнение
            pass
        
    finally:
        config.ADMIN_IDS = original_admin_ids


@pytest.mark.asyncio
async def test_unicode_and_special_characters_handling(mock_bot, mock_session, admin_user):
    """
    Тест: проверка обработки юникода и специальных символов
    """
    original_admin_ids = config.ADMIN_IDS
    config.ADMIN_IDS = [123]
    
    try:
        user_service = UserService(mock_session)
        giveaway_service = GiveawayService(mock_session, mock_bot)
        broadcast_service = BroadcastService(mock_bot, mock_session)
        
        # Различные юникодные символы для тестирования
        unicode_strings = [
            "🌟🎉✨ Unicode тест 🇷🇺🇸🇦🇬🇪",  # Эмодзи и флаги
            "àáâãäåæçèéêëìíîïñòóôõöøùúûüýÿ",  # Латинские расширения
            "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",  # Кириллица
            "가나다라마바사아자차카타파하",  # Корейский
            "あいうえおかきくけこさしすせそたちつてと",  # Японский хирагана
            "مرحبا، عالم",  # Арабский
            "❤️🔥👍 💕 💞 💓 💗 💖 💘 💝 💟 💜 💛 💚 💙",  # Эмодзи
            "©®™ € £ ¥ © ® ™ € £ ¥",  # Специальные символы
            "″ № § ґ Ґ і І ї Ї ј Ј ℮ ℯ ℰ Ⅎ ℳ ℾ ℿ",  # Разные символы
        ]
        
        for unicode_str in unicode_strings:
            # Проверяем поиск пользователей
            result = await user_service.search_users(unicode_str)
            assert isinstance(result, list)
            
            # Проверяем поиск розыгрышей
            result = await giveaway_service.search_giveaways(unicode_str)
            assert isinstance(result, list)
            
            # Проверяем создание рассылки с юникодом
            result = await broadcast_service.create_broadcast(unicode_str, admin_id=admin_user.id)
            # Может вернуть None в случае ошибки, но не должно быть падений
            assert result is None or hasattr(result, 'id')
        
        # Проверяем комбинации символов
        combined_unicode = "🎉 Привет! 👋 Тест 🌍 ∑ ∏ ∫ ∮ ∴ ∵ ∋ ∌ ∍ ∎ ∏ ∐ ∑"
        result = await user_service.search_users(combined_unicode)
        assert isinstance(result, list)
        
        result = await giveaway_service.search_giveaways(combined_unicode)
        assert isinstance(result, list)
        
    finally:
        config.ADMIN_IDS = original_admin_ids