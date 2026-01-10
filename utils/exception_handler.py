import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def handle_exceptions(default_return=None):
    """
    Декоратор для централизованной обработки исключений
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                return default_return
        return wrapper
    return decorator


# Обработчик ошибок для всего роутера
def admin_errors_handler(update, error):
    logger.error(f"Admin router error: {error}", exc_info=True)
    # Можно отправить уведомление администратору о критической ошибке