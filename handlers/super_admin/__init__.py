from . import (
    admin_base,
    stats_handler,
    users_handler,
    giveaways_handler,
    broadcast_handler,
    security_handler,
    settings_handler,
    logs_handler
)

from .admin_base import router as admin_base_router
from .stats_handler import router as stats_router
from .users_handler import router as users_router
from .giveaways_handler import router as giveaways_router
from .broadcast_handler import router as broadcast_router
from .security_handler import router as security_router
from .settings_handler import router as settings_router
from .logs_handler import router as logs_router

__all__ = [
    "admin_base",
    "stats_handler",
    "users_handler",
    "giveaways_handler",
    "broadcast_handler",
    "security_handler",
    "settings_handler",
    "logs_handler",
    # Роутеры
    "admin_base_router",
    "stats_router",
    "users_router",
    "giveaways_router",
    "broadcast_router",
    "security_router",
    "settings_router",
    "logs_router"
]