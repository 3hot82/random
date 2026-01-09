from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from keyboards.callback_data import StatsAction, NavigationAction, UsersAction, GiveawaysAction, GiveawaysPagination


def stats_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура раздела статистики с подменю"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Общая статистика", callback_data=StatsAction(action="main").pack())
    kb.button(text="📈 Рост пользователей", callback_data=StatsAction(action="growth").pack())
    kb.button(text="⭐ Премиум статистика", callback_data=StatsAction(action="premium").pack())
    kb.button(text="🎮 Розыгрыши", callback_data=StatsAction(action="giveaways").pack())
    kb.button(text="🎯 Участия", callback_data=StatsAction(action="participations").pack())
    kb.button(text="🔄 Обновить", callback_data=StatsAction(action="refresh").pack())
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def stats_growth_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики роста пользователей"""
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Новые за сегодня", callback_data=StatsAction(action="growth_today").pack())
    kb.button(text="📅 Новые за неделю", callback_data=StatsAction(action="growth_week").pack())
    kb.button(text="📆 Новые за месяц", callback_data=StatsAction(action="growth_month").pack())
    kb.button(text="🔙 Назад в статистику", callback_data=StatsAction(action="main").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def stats_premium_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для премиум статистики"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Общая статистика", callback_data=StatsAction(action="premium_overview").pack())
    kb.button(text="💰 Конверсия", callback_data=StatsAction(action="premium_conversion").pack())
    kb.button(text="📈 Рост премиум", callback_data=StatsAction(action="premium_growth").pack())
    kb.button(text="🔙 Назад в статистику", callback_data=StatsAction(action="main").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def stats_giveaways_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики розыгрышей"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Активные", callback_data=StatsAction(action="giveaways_active").pack())
    kb.button(text="🔴 Завершенные", callback_data=StatsAction(action="giveaways_finished").pack())
    kb.button(text="🎯 Среднее участников", callback_data=StatsAction(action="giveaways_avg").pack())
    kb.button(text="🔙 Назад в статистику", callback_data=StatsAction(action="main").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def stats_participations_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для статистики участий"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎫 Общее количество", callback_data=StatsAction(action="participations_total").pack())
    kb.button(text="📊 Среднее на розыгрыш", callback_data=StatsAction(action="participations_avg").pack())
    kb.button(text="🔙 Назад в статистику", callback_data=StatsAction(action="main").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def stats_refresh_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для обновления статистики"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=StatsAction(action="refresh").pack())
    kb.button(text="🔙 Назад в статистику", callback_data=StatsAction(action="main").pack())
    kb.adjust(2)
    return kb.as_markup()


def users_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела управления пользователями"""
    from keyboards.callback_data import UsersAction
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Поиск пользователя", callback_data=UsersAction(action="search").pack())
    kb.button(text="📋 Список пользователей", callback_data=UsersAction(action="list", page=1).pack())
    kb.button(text="⭐ Премиум-пользователи", callback_data=UsersAction(action="premium_list", page=1).pack())
    kb.button(text="🔒 Заблокированные пользователи", callback_data=UsersAction(action="blocked_list", page=1).pack())
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def giveaways_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура раздела розыгрышей"""
    from keyboards.callback_data import GiveawaysAction, NavigationAction
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Все розыгрыши", callback_data=GiveawaysAction(action="list", page=1).pack())
    kb.button(text="🔍 Поиск розыгрыша", callback_data=GiveawaysAction(action="search").pack())
    kb.button(text="筛选 Фильтр", callback_data=GiveawaysAction(action="filter").pack())
    kb.button(text="📊 Статистика розыгрышей", callback_data="giveaways_stats")
    kb.button(text="➕ Создать розыгрыш", callback_data="create_giveaway")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(1, 1, 1, 1, 1, 1)  # Большие кнопки
    return kb.as_markup()


def giveaways_list_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка розыгрышей с пагинацией"""
    from keyboards.callback_data import GiveawaysPagination, GiveawaysAction
    kb = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    if current_page > 1:
        kb.button(text="⬅️", callback_data=GiveawaysPagination(action="prev", page=current_page - 1).pack())
    
    kb.button(text=f"{current_page}/{total_pages}", callback_data="ignore")
    
    if current_page < total_pages:
        kb.button(text="➡️", callback_data=GiveawaysPagination(action="next", page=current_page + 1).pack())
    
    # Кнопки управления
    kb.button(text="🔄 Обновить", callback_data=GiveawaysAction(action="list", page=current_page).pack())
    kb.button(text="🔍 Поиск", callback_data=GiveawaysAction(action="search").pack())
    kb.button(text="筛选 Фильтр", callback_data=GiveawaysAction(action="filter").pack())
    kb.button(text="➕ Создать", callback_data="create_giveaway")
    kb.button(text="🔙 Назад", callback_data=GiveawaysAction(action="main").pack())
    kb.adjust(1, 1, 1, 1, 1)  # Большие кнопки
    return kb.as_markup()


def giveaway_detail_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления конкретным розыгрышем"""
    from keyboards.callback_data import GiveawaysAction, NavigationAction
    kb = InlineKeyboardBuilder()
    kb.button(text="🕹️ Завершить", callback_data=GiveawaysAction(action="finish", giveaway_id=giveaway_id).pack())
    kb.button(text="🗑 Удалить", callback_data=GiveawaysAction(action="delete", giveaway_id=giveaway_id).pack())
    kb.button(text="✏️ Редактировать", callback_data=GiveawaysAction(action="edit", giveaway_id=giveaway_id).pack())
    kb.button(text="👥 Участники", callback_data=GiveawaysAction(action="participants", giveaway_id=giveaway_id).pack())
    kb.button(text="🎲 Определить победителя", callback_data=GiveawaysAction(action="rig", giveaway_id=giveaway_id).pack())
    kb.button(text="📥 Экспорт", callback_data=GiveawaysAction(action="export", giveaway_id=giveaway_id).pack())
    kb.button(text="📋 Статистика", callback_data=f"giveaway_stats_{giveaway_id}")
    kb.button(text="🔙 Назад к списку", callback_data=GiveawaysAction(action="list", page=1).pack())
    kb.adjust(1, 1, 1, 1, 1, 1, 1, 1)  # Большие кнопки
    return kb.as_markup()


def broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела рассылки"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Создать рассылку", callback_data="admin_create_broadcast")
    kb.button(text="📊 Статус рассылки", callback_data="admin_broadcast_status")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def security_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела безопасности"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🚨 Подозрительные действия", callback_data="admin_suspicious")
    kb.button(text="🔒 Блокировка IP", callback_data="admin_block_ip")
    kb.button(text="📋 Логи безопасности", callback_data="admin_security_logs")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела настроек"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Общие настройки", callback_data="admin_general_settings")
    kb.button(text="🔐 Настройки безопасности", callback_data="admin_security_settings")
    kb.button(text="💾 Резервное копирование", callback_data="admin_backup")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def logs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела логов"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Логи пользователей", callback_data="admin_user_logs")
    kb.button(text="🔧 Логи ошибок", callback_data="admin_error_logs")
    kb.button(text="👤 Логи администраторов", callback_data="admin_admin_logs")
    kb.button(text="📤 Экспорт логов", callback_data="admin_export_logs")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура админ-панели"""
    from keyboards.callback_data import StatsAction
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data=StatsAction(action="main").pack())
    kb.button(text="👥 Пользователи", callback_data="admin_users")
    kb.button(text="🎮 Розыгрыши", callback_data="admin_giveaways")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="🛡 Безопасность", callback_data="admin_security")
    kb.button(text="⚙️ Настройки", callback_data="admin_settings")
    kb.button(text="📋 Логи", callback_data="admin_logs")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления конкретным пользователем"""
    from keyboards.callback_data import UsersAction, NavigationAction
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Выдать премиум", callback_data=UsersAction(action="grant_premium", user_id=user_id).pack())
    kb.button(text="🚫 Снять премиум", callback_data=UsersAction(action="revoke_premium", user_id=user_id).pack())
    kb.button(text="🔒 Заблокировать", callback_data=UsersAction(action="block", user_id=user_id).pack())
    kb.button(text="✅ Разблокировать", callback_data=UsersAction(action="unblock", user_id=user_id).pack())
    kb.button(text="📊 Статистика пользователя", callback_data=UsersAction(action="stats", user_id=user_id).pack())
    kb.button(text="🔙 Назад к списку", callback_data=UsersAction(action="list", page=1).pack())
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def giveaways_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела управления розыгрышами"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Все розыгрыши", callback_data="admin_list_giveaways")
    kb.button(text="🔍 Поиск розыгрыша", callback_data="admin_search_giveaway")
    kb.button(text="🕹️ Принудительное завершение", callback_data="admin_force_finish")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(1, 1, 1, 1)  # Большие кнопки
    return kb.as_markup()


def broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела рассылки"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Создать рассылку", callback_data="admin_create_broadcast")
    kb.button(text="📊 Статус рассылки", callback_data="admin_broadcast_status")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def security_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела безопасности"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🚨 Подозрительные действия", callback_data="admin_suspicious")
    kb.button(text="🔒 Блокировка IP", callback_data="admin_block_ip")
    kb.button(text="📋 Логи безопасности", callback_data="admin_security_logs")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела настроек"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Общие настройки", callback_data="admin_general_settings")
    kb.button(text="🔐 Настройки безопасности", callback_data="admin_security_settings")
    kb.button(text="💾 Резервное копирование", callback_data="admin_backup")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 1)
    return kb.as_markup()


def logs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела логов"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Логи пользователей", callback_data="admin_user_logs")
    kb.button(text="🔧 Логи ошибок", callback_data="admin_error_logs")
    kb.button(text="👤 Логи администраторов", callback_data="admin_admin_logs")
    kb.button(text="📤 Экспорт логов", callback_data="admin_export_logs")
    kb.button(text="🔙 Назад", callback_data=NavigationAction(action="back").pack())
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def build_manage_menu(giveaway_id: int, admin_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления розыгрышем"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⏹️ Завершить", callback_data=f"admin_finish_gw_{giveaway_id}")
    kb.button(text="🗑 Удалить", callback_data=f"admin_delete_gw_{giveaway_id}")
    kb.button(text="🎲 Определить победителя", callback_data=f"admin_rig_gw_{giveaway_id}")
    kb.button(text="🔙 Назад", callback_data="admin_giveaways")
    kb.adjust(1, 1, 1, 1)  # Большие кнопки
    return kb.as_markup()


def pagination_keyboard(current_page: int, total_pages: int, callback_data_prefix: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для пагинации"""
    kb = InlineKeyboardBuilder()
    
    # Кнопки навигации
    if current_page > 1:
        kb.button(text="⬅️", callback_data=f"{callback_data_prefix}_page_{current_page - 1}")
    
    kb.button(text=f"{current_page}/{total_pages}", callback_data="ignore")
    
    if current_page < total_pages:
        kb.button(text="➡️", callback_data=f"{callback_data_prefix}_page_{current_page + 1}")
    
    # Кнопка "Назад"
    kb.button(text="🔙 Назад", callback_data=UsersAction(action="main").pack())
    kb.adjust(1, 1, 1)
    return kb.as_markup()