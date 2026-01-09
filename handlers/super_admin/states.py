from aiogram.fsm.state import StatesGroup, State


class AdminGiveawayState(StatesGroup):
    waiting_for_giveaway_id = State()
    waiting_for_edit_param = State()
    waiting_for_edit_value = State()
    waiting_for_user_id_for_rig = State()