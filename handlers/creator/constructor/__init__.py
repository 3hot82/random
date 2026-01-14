from aiogram import Router
from . import start_content, settings, channels_select, channels_add, publication, winners_selector, referral_selector, control_message

router = Router()

router.include_router(start_content.router)
router.include_router(settings.router)
router.include_router(channels_select.router)
router.include_router(channels_add.router)
router.include_router(publication.router)
router.include_router(winners_selector.router)
router.include_router(referral_selector.router)
router.include_router(control_message.router)