from .db_session import DbSessionMiddleware
from .throttling import ThrottlingMiddleware
from .error_handler import ErrorMiddleware
from .admin_middleware import AdminRateLimitMiddleware
from .updates_filter import UpdatesFilterMiddleware  # <--- Добавлено

__all__ = [
    "DbSessionMiddleware",
    "ThrottlingMiddleware", 
    "ErrorMiddleware",
    "AdminRateLimitMiddleware",
    "UpdatesFilterMiddleware" # <--- Добавлено
]