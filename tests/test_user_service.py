import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from core.services.user_service import UserService


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    
    # Мокаем часто используемые методы сессии
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    
    return session


@pytest.fixture
def mock_bot():
    """Фикстура для мокирования бота"""
    bot = AsyncMock()
    return bot


@pytest.mark.asyncio
class TestUserService:
    """Тесты для сервиса работы с пользователями"""

    async def test_get_user_info_safe_success(self, mock_bot):
        """Тест безопасного получения информации о пользователе"""
        user_id = 123456789
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.username = "test_user"
        mock_user.is_bot = False
        mock_user.language_code = "en"
        
        mock_bot.get_chat.return_value = mock_user
        
        result = await UserService.get_user_info_safe(mock_bot, user_id)
        
        assert result is not None
        assert result['id'] == user_id
        assert result['first_name'] == "Test"
        assert result['full_name'] == "Test User"

    async def test_get_user_info_safe_telegram_error(self, mock_bot):
        """Тест обработки ошибки Telegram при получении информации о пользователе"""
        from aiogram.exceptions import TelegramBadRequest
        user_id = 123456789
        
        mock_bot.get_chat.side_effect = TelegramBadRequest(method="getChat", message="User not found")
        
        result = await UserService.get_user_info_safe(mock_bot, user_id)
        
        assert result is None

    async def test_get_user_info_safe_generic_error(self, mock_bot):
        """Тест обработки общей ошибки при получении информации о пользователе"""
        user_id = 123456789
        
        mock_bot.get_chat.side_effect = Exception("Network error")
        
        result = await UserService.get_user_info_safe(mock_bot, user_id)
        
        assert result is None

    async def test_get_user_from_db_success(self, mock_session):
        """Тест получения пользователя из базы данных"""
        user_id = 123456789
        mock_user = User(
            user_id=user_id,
            username="db_user",
            full_name="DB User",
            is_premium=False
        )
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        result = await UserService.get_user_from_db(mock_session, user_id)
        
        assert result == mock_user
        assert result.user_id == user_id

    async def test_get_user_from_db_not_found(self, mock_session):
        """Тест получения несуществующего пользователя из базы данных"""
        user_id = 999999999  # Не существует
        
        async def mock_get(model, identifier):
            return None
            
        mock_session.get = mock_get
        
        result = await UserService.get_user_from_db(mock_session, user_id)
        
        assert result is None

    async def test_get_user_from_db_error(self, mock_session):
        """Тест обработки ошибки при получении пользователя из базы данных"""
        user_id = 123456789
        
        async def mock_get(model, identifier):
            raise Exception("Database error")
            
        mock_session.get = mock_get
        
        result = await UserService.get_user_from_db(mock_session, user_id)
        
        assert result is None

    async def test_register_user_safe_success(self, mock_session):
        """Тест безопасной регистрации пользователя"""
        user_id = 123456789
        username = "test_user"
        full_name = "Test User"
        
        # Мокаем успешное выполнение
        mock_session.execute = AsyncMock()
        
        result = await UserService.register_user_safe(mock_session, user_id, username, full_name)
        
        assert result is True
        mock_session.execute.assert_called()

    async def test_register_user_safe_error(self, mock_session):
        """Тест обработки ошибки при безопасной регистрации пользователя"""
        user_id = 123456789
        username = "error_user"
        full_name = "Error User"
        
        # Мокаем ошибку при выполнении запроса
        mock_session.execute.side_effect = Exception("Database error")
        
        result = await UserService.register_user_safe(mock_session, user_id, username, full_name)
        
        assert result is False

    async def test_update_user_info_success(self, mock_session):
        """Тест обновления информации о пользователе"""
        user_id = 123456789
        new_username = "updated_user"
        new_full_name = "Updated User Name"
        
        # Создаем мок-пользователя
        mock_user = User(
            user_id=user_id,
            username="old_user",
            full_name="Old User Name",
            is_premium=False
        )
        
        # Мокаем возврат пользователя
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        result = await UserService.update_user_info(mock_session, user_id, new_username, new_full_name)
        
        assert result is True
        assert mock_user.username == new_username
        assert mock_user.full_name == new_full_name
        mock_session.commit.assert_called_once()

    async def test_update_user_info_user_not_found_then_register(self, mock_session):
        """Тест обновления информации о несуществующем пользователе (регистрация нового)"""
        user_id = 123456789  # Теперь используем существующий ID
        new_username = "new_user"
        new_full_name = "New User Name"
        
        # Мокаем возврат None для первого вызова (пользователь не найден), 
        # затем создаем нового пользователя и возвращаем его
        call_count = 0
        
        async def mock_get(model, identifier):
            nonlocal call_count
            if call_count == 0 and model == User and identifier == user_id:
                call_count += 1
                return None  # Первый вызов - пользователь не найден
            elif model == User and identifier == user_id:
                # После регистрации возвращаем нового пользователя
                return User(user_id=user_id, username=new_username, full_name=new_full_name, is_premium=False)
            return None
            
        mock_session.get = mock_get
        mock_session.execute = AsyncMock()  # Мокаем выполнение для регистрации
        
        result = await UserService.update_user_info(mock_session, user_id, new_username, new_full_name)
        
        # Результат должен быть True, так как функция должна зарегистрировать пользователя
        assert result is True

    async def test_update_user_info_partial_update(self, mock_session):
        """Тест частичного обновления информации о пользователе"""
        user_id = 123456789
        mock_user = User(
            user_id=user_id,
            username="old_user",
            full_name="Old User Name",
            is_premium=False
        )
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        # Обновляем только имя пользователя
        result = await UserService.update_user_info(mock_session, user_id, username="updated_username")
        
        assert result is True
        assert mock_user.username == "updated_username"
        assert mock_user.full_name == "Old User Name"  # Не изменилось
        mock_session.commit.assert_called_once()

    async def test_update_user_info_premium_flag(self, mock_session):
        """Тест обновления премиум-флага пользователя"""
        user_id = 123456789
        mock_user = User(
            user_id=user_id,
            username="premium_user",
            full_name="Premium User",
            is_premium=False
        )
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        
        # Обновляем только премиум-флаг
        result = await UserService.update_user_info(mock_session, user_id, is_premium=True)
        
        assert result is True
        assert mock_user.is_premium is True
        mock_session.commit.assert_called_once()

    async def test_update_user_info_error(self, mock_session):
        """Тест обработки ошибки при обновлении информации о пользователе"""
        user_id = 123456789
        mock_user = User(
            user_id=user_id,
            username="old_user",
            full_name="Old User Name",
            is_premium=False
        )
        
        async def mock_get(model, identifier):
            if model == User and identifier == user_id:
                return mock_user
            return None
            
        mock_session.get = mock_get
        # Мокаем ошибку при коммите
        mock_session.commit.side_effect = Exception("Database error")
        
        result = await UserService.update_user_info(mock_session, user_id, "new_username", "New Full Name")
        
        assert result is False

    async def test_is_user_admin_success(self, mock_bot):
        """Тест проверки статуса администратора пользователя"""
        chat_id = -1001234567890
        user_id = 123456789
        mock_member = MagicMock()
        mock_member.status = "administrator"
        
        mock_bot.get_chat_member.return_value = mock_member
        
        result = await UserService.is_user_admin(mock_bot, chat_id, user_id)
        
        assert result is True
        mock_bot.get_chat_member.assert_called_once_with(chat_id=chat_id, user_id=user_id)

    async def test_is_user_admin_creator(self, mock_bot):
        """Тест проверки статуса создателя чата"""
        chat_id = -1001234567890
        user_id = 123456789
        mock_member = MagicMock()
        mock_member.status = "creator"
        
        mock_bot.get_chat_member.return_value = mock_member
        
        result = await UserService.is_user_admin(mock_bot, chat_id, user_id)
        
        assert result is True

    async def test_is_user_admin_not_admin(self, mock_bot):
        """Тест проверки, что пользователь не является администратором"""
        chat_id = -1001234567890
        user_id = 123456789
        mock_member = MagicMock()
        mock_member.status = "member"
        
        mock_bot.get_chat_member.return_value = mock_member
        
        result = await UserService.is_user_admin(mock_bot, chat_id, user_id)
        
        assert result is False

    async def test_is_user_admin_telegram_error(self, mock_bot):
        """Тест обработки ошибки Telegram при проверке статуса администратора"""
        from aiogram.exceptions import TelegramBadRequest
        chat_id = -1001234567890
        user_id = 123456789
        
        mock_bot.get_chat_member.side_effect = TelegramBadRequest(method="getChatMember", message="Chat not found")
        
        result = await UserService.is_user_admin(mock_bot, chat_id, user_id)
        
        assert result is False

    async def test_is_user_admin_generic_error(self, mock_bot):
        """Тест обработки общей ошибки при проверке статуса администратора"""
        chat_id = -1001234567890
        user_id = 123456789
        
        mock_bot.get_chat_member.side_effect = Exception("Network error")
        
        result = await UserService.is_user_admin(mock_bot, chat_id, user_id)
        
        assert result is False