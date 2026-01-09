# handlers/user/__init__.py
from aiogram import Router

from . import dashboard, my_channels, my_participations, my_giveaways, premium

router = Router()

# Include sub-routers
router.include_router(dashboard.router)
router.include_router(my_channels.router)
router.include_router(my_participations.router)
router.include_router(my_giveaways.router)
router.include_router(premium.router)