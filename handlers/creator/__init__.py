# handlers/creator/__init__.py
from aiogram import Router

from . import time_picker
from . import constructor

router = Router()

# Include sub-routers
router.include_router(time_picker.router)
router.include_router(constructor.router)