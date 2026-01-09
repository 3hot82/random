from aiogram import Router
from .list_view import router as list_view_router
from .manage_item import router as manage_item_router

router = Router()

# Include sub-routers
router.include_router(list_view_router)
router.include_router(manage_item_router)

__all__ = ["list_view_router", "manage_item_router", "router"]