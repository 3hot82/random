from aiogram.filters.callback_data import CallbackData
from typing import Optional


class GiveawayAction(CallbackData, prefix="giveaway"):
    action: str
    giveaway_id: int


class GiveawaysPagination(CallbackData, prefix="gwp"):
    """
    Callback data для пагинации розыгрышей
    action: prev, next
    page: номер страницы
    filter_status: статус фильтра (active, finished, pending)
    """
    action: str
    page: int
    filter_status: str = ""
