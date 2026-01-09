from typing import Optional
from aiogram import Dispatcher
from aiogram.types import Update
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError
)


class BaseBotException(Exception):
    """Базовое исключение для бота"""
    def __init__(self, message: str, user_id: Optional[int] = None, action: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.action = action


class DatabaseError(BaseBotException):
    """Исключение для ошибок базы данных"""
    pass


class SubscriptionError(BaseBotException):
    """Исключение для ошибок проверки подписки"""
    pass


class GiveawayError(BaseBotException):
    """Исключение для ошибок розыгрышей"""
    pass


class ValidationError(BaseBotException):
    """Исключение для ошибок валидации"""
    pass


class ErrorHandler:
    """Централизованный обработчик ошибок"""
    
    def __init__(self):
        self.logger = None
    
    def setup_logger(self):
        """Настройка логгера"""
        import logging
        self.logger = logging.getLogger("ErrorHandler")
    
    async def handle_error(self, error: Exception, user_id: Optional[int] = None, action: Optional[str] = None):
        """Обработка ошибки с логированием"""
        if not self.logger:
            self.setup_logger()
        
        # Определяем тип ошибки и логируем соответствующим образом
        if isinstance(error, TelegramBadRequest):
            self.logger.error(
                f"TelegramBadRequest | User: {user_id} | Action: {action} | Error: {str(error)}"
            )
        elif isinstance(error, TelegramNetworkError):
            self.logger.error(
                f"TelegramNetworkError | User: {user_id} | Action: {action} | Error: {str(error)}"
            )
        elif isinstance(error, TelegramRetryAfter):
            self.logger.warning(
                f"TelegramRetryAfter | User: {user_id} | Action: {action} | Retry after: {error.retry_after}s"
            )
        elif isinstance(error, TelegramServerError):
            self.logger.error(
                f"TelegramServerError | User: {user_id} | Action: {action} | Error: {str(error)}"
            )
        elif isinstance(error, BaseBotException):
            self.logger.error(
                f"BaseBotException | User: {user_id} | Action: {action} | Error: {str(error)}"
            )
        else:
            self.logger.error(
                f"UnexpectedError | User: {user_id} | Action: {action} | Error: {str(error)} | Type: {type(error)}"
            )
    
    async def handle_update_error(self, dispatcher: Dispatcher, update: Update, error: Exception):
        """Обработка ошибки обновления"""
        user_id = None
        action = None
        
        # Извлекаем информацию из обновления
        if update.message:
            user_id = update.message.from_user.id
            action = f"message_{update.message.text[:50] if update.message.text else 'unknown'}"
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            action = f"callback_{update.callback_query.data[:50] if update.callback_query.data else 'unknown'}"
        elif update.inline_query:
            user_id = update.inline_query.from_user.id
            action = f"inline_query_{update.inline_query.query[:50] if update.inline_query.query else 'unknown'}"
        elif update.chosen_inline_result:
            user_id = update.chosen_inline_result.from_user.id
            action = f"chosen_inline_result_{update.chosen_inline_result.result_id}"
        
        await self.handle_error(error, user_id, action)


# Глобальный экземпляр обработчика ошибок
error_handler = ErrorHandler()