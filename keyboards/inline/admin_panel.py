# Этот файл был объединен с admin_keyboards.py
# Все функции клавиатур теперь находятся в AdminKeyboardFactory в admin_keyboards.py
from ..admin_keyboards import AdminKeyboardFactory

# Оставляем для обратной совместимости, если где-то использовались напрямую
stats_main_keyboard = AdminKeyboardFactory.create_stats_menu
users_keyboard = AdminKeyboardFactory.create_users_menu
giveaways_main_keyboard = AdminKeyboardFactory.create_giveaways_menu
giveaway_detail_keyboard = AdminKeyboardFactory.create_giveaway_detail_menu
broadcast_keyboard = AdminKeyboardFactory.create_broadcast_menu
security_keyboard = AdminKeyboardFactory.create_security_menu
settings_keyboard = AdminKeyboardFactory.create_settings_menu
logs_keyboard = AdminKeyboardFactory.create_logs_menu
admin_main_menu_keyboard = AdminKeyboardFactory.create_main_menu
user_detail_keyboard = AdminKeyboardFactory.create_user_detail_menu
giveaways_list_keyboard = lambda current_page, total_pages: AdminKeyboardFactory.create_giveaways_menu()
build_manage_menu = lambda giveaway_id: AdminKeyboardFactory.create_giveaway_detail_menu(giveaway_id)
pagination_keyboard = lambda current_page, total_pages, callback_data_prefix: AdminKeyboardFactory.create_back_button()
