from .common.start import router as start_router
from .user import *
from .creator import *
from .participant import *
from .admin import *

__all__ = [
    "start_router",
    # user routers
    "dashboard_router",
    "my_channels_router", 
    "my_giveaways_router",
    "my_participations_router",
    "premium_router",
    # creator routers
    "creator_router",
    "time_picker_router",
    # constructor routers
    "constructor_router",
    "channels_add_router",
    "channels_select_router",
    "control_message_router",
    "message_manager_router",
    "publication_router",
    "referral_selector_router",
    "settings_router",
    "start_content_router",
    "structure_router",
    "winners_selector_router",
    # participant routers
    "join_router",
    # admin routers
    "admin_router"
]