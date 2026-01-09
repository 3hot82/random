from aiogram import Router
from .giveaways.list_view import router as list_view_router
from .giveaways.manage_item import router as manage_item_router

# Основной роутер для розыгрышей
router = Router()

# Включение подроутеров
router.include_router(list_view_router)
router.include_router(manage_item_router)

__all__ = ["router"]